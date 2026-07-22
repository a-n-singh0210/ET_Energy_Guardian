"""api.py — Flask JSON API over the EnergyGuardian backend.

A thin serving layer for a decoupled frontend (e.g. a Lovable-built React app).
It contains **no business logic** — it runs the existing backend pipeline once,
caches the frames, and exposes them as JSON. All computation lives in
ingestion / features / anomalies / compound / baseline / validate / explain.

Run::

    python api.py            # serves on http://localhost:5001

Environment:
    ENERGYGUARDIAN_API_PORT  override port (default 5001)

CORS is enabled so a browser-hosted frontend can call this API in development.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

# Load API keys (e.g. GEMINI_API_KEY) from a local .env file if present.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # dotenv is optional; env vars still work without it
    pass

# Backend modules (all calculation lives here).
import validate
from anomalies import compute_anomalies
from baseline import BASELINE_THRESHOLDS, apply_thresholds
from compound import LAMBDA, RISK_LEVELS, WEIGHTS, compute_compound
from explain import explain_day
from features import build_features
from ingestion import build_merged, load_events

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"

app = Flask(__name__)
CORS(app)  # allow cross-origin calls from the frontend in development

_CACHE: dict[str, Any] = {}


def _clean(value: Any) -> Any:
    """Convert non-JSON-safe floats (NaN/inf) to None."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def to_records(df: pd.DataFrame, index_name: str = "date") -> list[dict[str, Any]]:
    """Convert a date-indexed DataFrame to a list of JSON-safe records.

    Args:
        df: DataFrame indexed by date.
        index_name: Name to give the index column in each record.

    Returns:
        List of dicts with ISO date strings and NaN replaced by None.
    """
    d = df.reset_index()
    first = d.columns[0]
    d = d.rename(columns={first: index_name})
    d[index_name] = d[index_name].apply(
        lambda x: x.date().isoformat() if hasattr(x, "date") else str(x)
    )
    records = d.to_dict(orient="records")
    return [{k: _clean(v) for k, v in rec.items()} for rec in records]


def pipeline() -> dict[str, Any]:
    """Run the backend pipeline once and cache every frame the API serves.

    Returns:
        Cached dict of computed frames and ground-truth events.
    """
    if _CACHE:
        return _CACHE

    merged = build_merged(save=False)
    features = build_features(merged)
    anomalies = compute_anomalies(features)
    compound = compute_compound(anomalies)
    baseline = apply_thresholds(anomalies)
    events = load_events()
    gt = events.loc[events["severity"] >= validate.GT_SEVERITY_MIN, "date"].sort_values()
    gt = gt.reset_index(drop=True)

    joined = (
        merged[["events", "n_events", "event_severity_sum"]]
        .join(features[["brent_return", "freight_wci_ffill", "event_severity_14"]])
        .join(anomalies)
        .join(compound)
    )

    _CACHE.update(
        merged=merged,
        features=features,
        anomalies=anomalies,
        compound=compound,
        baseline=baseline,
        events=events,
        gt=gt,
        joined=joined,
    )
    return _CACHE


@app.get("/api/health")
def health() -> Any:
    """Liveness check."""
    return jsonify({"status": "ok"})


@app.get("/api/overview")
def overview() -> Any:
    """Headline stats, risk distribution, comparison and model parameters."""
    d = pipeline()
    compound, baseline, gt = d["compound"], d["baseline"], d["gt"]
    peak_ts = compound["compound_score"].idxmax()
    comparison = validate.compare(compound, baseline, gt)

    dist = compound["risk_level"].value_counts().to_dict()
    return jsonify(
        {
            "window": {
                "start": compound.index.min().date().isoformat(),
                "end": compound.index.max().date().isoformat(),
            },
            "n_days": int(len(compound)),
            "peak": {
                "date": peak_ts.date().isoformat(),
                "score": float(compound.loc[peak_ts, "compound_score"]),
                "risk_level": str(compound.loc[peak_ts, "risk_level"]),
            },
            "risk_distribution": {k: int(v) for k, v in dist.items()},
            "comparison": comparison.reset_index().to_dict(orient="records"),
            "signals": [
                {"key": "brent", "label": "Brent crude", "role": "Market-stress context"},
                {"key": "freight", "label": "Freight (WCI)", "role": "Shipping-cost dislocation"},
                {"key": "events", "label": "Corridor events", "role": "Red Sea disruption"},
            ],
            "parameters": {
                "weights": WEIGHTS,
                "lambda": LAMBDA,
                "risk_levels": [{"level": n, "lower_bound": (None if b == float("-inf") else b)} for n, b in RISK_LEVELS],
                "baseline_thresholds": BASELINE_THRESHOLDS,
                "compound_alert_threshold": validate.COMPOUND_ALERT_THRESHOLD,
            },
        }
    )


@app.get("/api/timeline")
def timeline() -> Any:
    """Documented event log plus the compound score / risk series."""
    d = pipeline()
    events = d["events"][["date", "event", "category", "severity"]].copy()
    events["date"] = events["date"].apply(lambda x: x.date().isoformat())
    score = d["compound"][["compound_score", "risk_level"]]
    return jsonify(
        {
            "events": [{k: _clean(v) for k, v in r.items()} for r in events.to_dict(orient="records")],
            "score_series": to_records(score),
        }
    )


@app.get("/api/signals")
def signals() -> Any:
    """Per-signal anomaly series and their underlying features."""
    d = pipeline()
    anomalies = d["anomalies"][["anomaly_brent", "anomaly_freight", "anomaly_events"]]
    feats = d["features"][["brent_return", "freight_wci_ffill", "event_severity_14"]]
    return jsonify({"anomalies": to_records(anomalies), "features": to_records(feats)})


@app.get("/api/compound")
def compound_series() -> Any:
    """Full compound decomposition series (contributions, totals, score, level)."""
    d = pipeline()
    return jsonify({"series": to_records(d["compound"])})


@app.get("/api/compare")
def compare() -> Any:
    """Baseline-vs-compound comparison, alert dates and threshold sensitivity."""
    d = pipeline()
    compound, baseline, gt = d["compound"], d["baseline"], d["gt"]
    comparison = validate.compare(compound, baseline, gt)
    sensitivity = validate.threshold_sensitivity(compound, gt)

    c_dates = [x.date().isoformat() for x in validate.compound_alert_dates(compound)]
    b_dates = [x.date().isoformat() for x in validate.baseline_alert_dates(baseline)]
    return jsonify(
        {
            "comparison": comparison.reset_index().to_dict(orient="records"),
            "compound_alert_dates": c_dates,
            "baseline_alert_dates": b_dates,
            "gt_events": [x.date().isoformat() for x in gt],
            "systemic_onset": validate.SYSTEMIC_ONSET,
            "compound_alert_threshold": validate.COMPOUND_ALERT_THRESHOLD,
            "sensitivity": [{k: _clean(v) for k, v in r.items()} for r in sensitivity.to_dict(orient="records")],
        }
    )


@app.get("/api/explanation/dates")
def explanation_dates() -> Any:
    """List of selectable days and the default (peak-risk) day."""
    d = pipeline()
    joined = d["joined"]
    dates = [x.date().isoformat() for x in joined.index]
    default = joined["compound_score"].idxmax().date().isoformat()
    return jsonify({"dates": dates, "default": default})


@app.get("/api/explanation")
def explanation() -> Any:
    """Traceable explanation for a given ?date=YYYY-MM-DD."""
    d = pipeline()
    date = request.args.get("date")
    if not date:
        date = d["joined"]["compound_score"].idxmax().date().isoformat()
    try:
        exp = explain_day(date, d["joined"])
    except KeyError:
        return jsonify({"error": f"date {date} not found"}), 404
    return jsonify({"date": exp.date, "text": exp.text, "trace": exp.trace})


@app.get("/api/assumptions")
def assumptions() -> Any:
    """Raw markdown of the assumptions register(s)."""
    parts = []
    for fname in ("india_assumptions.md", "assumptions.md"):
        p = DOCS_DIR / fname
        if p.exists():
            parts.append(p.read_text())
    return jsonify({"markdown": "\n\n---\n\n".join(parts)})


# --------------------------------------------------------------------------- #
# India energy-security resilience endpoints
# --------------------------------------------------------------------------- #
import time  # noqa: E402

import agents  # noqa: E402
import ais as ais_mod  # noqa: E402
import geodata  # noqa: E402
import india_params  # noqa: E402
import knowledge_graph  # noqa: E402
import news_agent  # noqa: E402
import rag as rag_mod  # noqa: E402
import scenario as scen  # noqa: E402

DISRUPTION_THRESHOLD = 0.15  # a corridor counts as "disrupted" above this fraction

# Simple TTL cache for the live intel feed (avoid re-fetching news every render).
_INTEL_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_INTEL_TTL = 600  # seconds


@app.get("/api/intel")
def intel() -> Any:
    """Live geopolitical risk intelligence (news ingest → extract → score).

    Cached for ``_INTEL_TTL`` seconds. Pass ``?refresh=1`` to force a re-fetch.
    """
    force = request.args.get("refresh") == "1"
    now = time.time()
    if force or _INTEL_CACHE["data"] is None or (now - _INTEL_CACHE["ts"]) > _INTEL_TTL:
        _INTEL_CACHE["data"] = news_agent.run_intel()
        _INTEL_CACHE["ts"] = now
    return jsonify({**_INTEL_CACHE["data"], "cache_age_seconds": int(now - _INTEL_CACHE["ts"])})


@app.post("/api/extract")
def extract() -> Any:
    """Extract one structured disruption signal from a pasted news article.

    Body: ``{"text": "<article text>"}``. Returns the extracted corridor,
    severity, event_type, confidence, a rationale, and the scenario knobs the
    signal maps onto (so the caller can run it through the impact model).
    """
    payload = request.get_json(silent=True) or {}
    return jsonify(news_agent.extract_article(payload.get("text", "")))


@app.get("/api/india/context")
def india_context() -> Any:
    """Static reference context: parameters, import mix, presets, geospatial data."""
    return jsonify(
        {
            "params": india_params.all_params(),
            "import_mix": india_params.IMPORT_MIX,
            "import_mix_source": india_params.IMPORT_MIX_SOURCE,
            "presets": {name: vars(inp) for name, inp in scen.PRESETS.items()},
            "geo": geodata.geo_payload(),
        }
    )


def _qf(name: str) -> float:
    """Parse an optional float query param, defaulting to 0."""
    try:
        return float(request.args.get(name, "0") or 0)
    except ValueError:
        return 0.0


@app.get("/api/resilience")
def resilience() -> Any:
    """Run the signal→scenario→response decision pipeline for a set of knobs.

    Query params (all optional floats): ``hormuz`` [0-1], ``redsea`` [0-1],
    ``opec`` (mb/d). The response is produced by the decision pipeline and
    includes the inspectable ``pipeline`` trace (each engine's inputs,
    reasoning and output).
    """
    return jsonify(agents.orchestrate(_qf("hormuz"), _qf("redsea"), _qf("opec")))


@app.get("/api/graph")
def graph() -> Any:
    """Knowledge graph (supplier ↔ corridor ↔ grade ↔ refinery) + impact.

    Optional ``hormuz`` / ``redsea`` params flag disrupted corridors and return
    a graph-traversal impact query (cut-off suppliers, at-risk volume/grades).
    Live corridor risk from the intel feed annotates corridor nodes when cached.
    """
    disrupted: set[str] = set()
    if _qf("hormuz") >= DISRUPTION_THRESHOLD:
        disrupted.add("hormuz")
    if _qf("redsea") >= DISRUPTION_THRESHOLD:
        disrupted.add("redsea")
    corridor_risk = {}
    if _INTEL_CACHE.get("data"):
        corridor_risk = _INTEL_CACHE["data"].get("corridor_scores", {})
    return jsonify(knowledge_graph.graph_payload(disrupted, corridor_risk))


_AIS_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
_AIS_TTL = 3600


@app.get("/api/ais")
def ais() -> Any:
    """AIS-derived chokepoint vessel traffic (IMF PortWatch). Cached 1h."""
    now = time.time()
    if _AIS_CACHE["data"] is None or (now - _AIS_CACHE["ts"]) > _AIS_TTL:
        _AIS_CACHE["data"] = ais_mod.fetch_chokepoints()
        _AIS_CACHE["ts"] = now
    return jsonify({"chokepoints": _AIS_CACHE["data"], "source": "IMF PortWatch (AIS-derived)"})


@app.get("/api/ask")
def ask() -> Any:
    """RAG over the geopolitical/commodity corpus. Query param ``q``."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"samples": rag_mod.SAMPLE_QUESTIONS})
    return jsonify(rag_mod.ask(q))


if __name__ == "__main__":
    port = int(os.environ.get("ENERGYGUARDIAN_API_PORT", "5001"))
    pipeline()  # warm the cache at startup
    app.run(host="0.0.0.0", port=port, debug=False)
