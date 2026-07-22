"""explain.py — Module 8: traceable explanations.

Builds a human-readable explanation for any day by walking the required chain:

    raw signals -> anomaly scores -> interaction contributions -> final score
    -> human-readable explanation

Every sentence is traceable to a number produced by an earlier module; the
explanation invents nothing — it is a fully deterministic template with no LLM
in the loop.

Run standalone::

    python explain.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

SIGNALS = ("brent", "freight", "events")


@dataclass
class Explanation:
    """A traceable explanation for one day.

    Attributes:
        date: ISO date string.
        trace: The audit trail (raw → anomalies → contributions → score).
        text: The rendered explanation (template, optionally LLM-reworded).
    """

    date: str
    trace: dict[str, Any] = field(default_factory=dict)
    text: str = ""


def _load_joined() -> pd.DataFrame:
    """Assemble one frame with raw signals, anomalies and compound outputs.

    Returns:
        DataFrame indexed by ``date`` joining merged raw values, engineered
        features, anomaly scores and the compound decomposition.
    """
    from anomalies import compute_anomalies
    from compound import compute_compound
    from features import build_features
    from ingestion import build_merged

    merged = build_merged(save=False)
    features = build_features(merged)
    anomalies = compute_anomalies(features)
    compound = compute_compound(anomalies)

    raw = merged[["events", "n_events", "event_severity_sum"]]
    feat = features[["brent_return", "freight_wci_ffill", "event_severity_14"]]
    return raw.join(feat).join(anomalies).join(compound)


def _fmt(value: Any) -> str:
    """Format a number for display, showing 'n/a' for missing values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def build_trace(row: pd.Series) -> dict[str, Any]:
    """Extract the full audit trail for one day's row.

    Args:
        row: A joined row (raw + anomalies + compound), typically from
            ``_load_joined()``.

    Returns:
        Nested dict with keys ``raw``, ``anomalies``, ``linear_contributions``,
        ``interaction_contributions``, ``final``.
    """
    raw = {
        "brent_return": float(row["brent_return"]) if pd.notna(row["brent_return"]) else None,
        "freight_wci_ffill": float(row["freight_wci_ffill"]) if pd.notna(row["freight_wci_ffill"]) else None,
        "event_severity_14": float(row["event_severity_14"]),
        "n_events": int(row["n_events"]),
        "events_text": str(row["events"]),
    }
    anomalies = {s: float(row[f"anomaly_{s}"]) for s in SIGNALS}
    linear = {s: float(row[f"signal_{s}"]) for s in SIGNALS}
    interactions = {
        f"{a}x{b}": float(row[f"int_{a}__{b}"]) for a, b in combinations(SIGNALS, 2)
    }
    final = {
        "linear_total": float(row["linear_total"]),
        "interaction_total": float(row["interaction_total"]),
        "compound_score": float(row["compound_score"]),
        "risk_level": str(row["risk_level"]),
    }
    return {
        "raw": raw,
        "anomalies": anomalies,
        "linear_contributions": linear,
        "interaction_contributions": interactions,
        "final": final,
    }


def render_template(date: str, trace: dict[str, Any]) -> str:
    """Render the traceable explanation following the required chain.

    Args:
        date: ISO date string.
        trace: Output of :func:`build_trace`.

    Returns:
        A multi-line, fully traceable explanation string.
    """
    raw, anomalies = trace["raw"], trace["anomalies"]
    linear, inter = trace["linear_contributions"], trace["interaction_contributions"]
    final = trace["final"]

    lines: list[str] = [f"[{date}] Risk level: {final['risk_level']} "
                        f"(compound score {final['compound_score']:.3f})."]

    # 1. Raw signals
    ev = raw["events_text"] if raw["events_text"] else "no corridor events"
    lines.append(
        "Raw signals — Brent return {br}, freight WCI {fr}, 14d event severity {es} "
        "({n} event(s): {ev}).".format(
            br=_fmt(raw["brent_return"]), fr=_fmt(raw["freight_wci_ffill"]),
            es=_fmt(raw["event_severity_14"]), n=raw["n_events"], ev=ev,
        )
    )

    # 2. Anomaly scores
    lines.append(
        "Anomaly scores (robust z, 14d) — brent {b}, freight {f}, events {e}.".format(
            b=_fmt(anomalies["brent"]), f=_fmt(anomalies["freight"]), e=_fmt(anomalies["events"])
        )
    )

    # 3. Interaction (and linear) contributions
    lines.append(
        "Linear contributions — " + ", ".join(f"{s} {linear[s]:+.3f}" for s in SIGNALS)
        + f" (sum {final['linear_total']:+.3f})."
    )
    lines.append(
        "Interaction contributions — " + ", ".join(f"{k} {v:.3f}" for k, v in inter.items())
        + f" (sum {final['interaction_total']:.3f})."
    )

    # 4/5. Final score + human-readable driver
    top_linear = max(SIGNALS, key=lambda s: abs(linear[s]))
    top_inter_key = max(inter, key=inter.get) if inter else None
    interaction_share = (
        final["interaction_total"] / final["compound_score"]
        if final["compound_score"] > 0 else 0.0
    )

    if final["interaction_total"] > 0 and interaction_share >= 0.15:
        driver = (
            f"This is a compound signal: the largest single contribution is {top_linear} "
            f"({linear[top_linear]:+.3f}), and co-elevation adds {final['interaction_total']:.3f} "
            f"(largest pair {top_inter_key} {inter[top_inter_key]:.3f}), "
            f"{interaction_share * 100:.0f}% of the score."
        )
    elif final["compound_score"] <= 0:
        driver = "Signals are calm or unusually low; no elevated risk indicated."
    else:
        driver = (
            f"The score is driven mainly by the {top_linear} linear term "
            f"({linear[top_linear]:+.3f}); interaction is small "
            f"({final['interaction_total']:.3f})."
        )
    lines.append("Explanation: " + driver)
    return "\n".join(lines)


def explain_day(date: str, joined: pd.DataFrame) -> Explanation:
    """Produce a traceable explanation for a single day.

    Args:
        date: ISO date string present in ``joined``.
        joined: The joined frame from ``_load_joined()``.

    Returns:
        An :class:`Explanation`.

    Raises:
        KeyError: If ``date`` is not in the frame.
    """
    ts = pd.Timestamp(date)
    if ts not in joined.index:
        raise KeyError(f"date {date} not found in data.")
    trace = build_trace(joined.loc[ts])
    text = render_template(date, trace)
    return Explanation(date=date, trace=trace, text=text)


if __name__ == "__main__":
    joined = _load_joined()

    print("=" * 84)
    print("MODULE 8 ACCEPTANCE — traceable explanations")
    print("=" * 84)
    print("Chain: raw signals -> anomaly scores -> interaction contributions -> "
          "final score -> explanation\n")

    # Representative days: the peak compound day, a single-signal (brent) day,
    # and a co-elevation day.
    peak = joined["compound_score"].idxmax().date().isoformat()
    for day in [peak, "2023-12-08", "2023-12-26"]:
        exp = explain_day(day, joined)
        print(exp.text)
        print("-" * 84)
