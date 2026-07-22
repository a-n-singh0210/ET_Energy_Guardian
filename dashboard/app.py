"""app.py — Module 9: Streamlit dashboard (visualization only).

The dashboard contains **no business logic**. Every number is computed by the
backend modules (ingestion → features → anomalies → compound → baseline →
validate → explain); this file only loads those outputs and renders them.

Pages: Timeline · Signals · Compound vs Baseline · Explanation · Assumptions ·
Replay.

Run from the v2 project root::

    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the backend modules (one level up) importable.
V2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2_ROOT))

from anomalies import compute_anomalies  # noqa: E402
from baseline import apply_thresholds  # noqa: E402
from compound import compute_compound  # noqa: E402
from explain import explain_day  # noqa: E402
from features import build_features  # noqa: E402
from ingestion import build_merged, load_events  # noqa: E402
import validate  # noqa: E402

DOCS_DIR = V2_ROOT / "docs"
FIGURES_DIR = V2_ROOT / "figures"


@st.cache_data(show_spinner="Running backend pipeline…")
def load_backend() -> dict[str, object]:
    """Run the backend pipeline once and return every frame the UI displays.

    This orchestrates backend calls only — no calculations happen here or in any
    page function; all maths lives in the imported modules.

    Returns:
        Dict of DataFrames/paths the pages render.
    """
    merged = build_merged(save=False)
    features = build_features(merged)
    anomalies = compute_anomalies(features)
    compound = compute_compound(anomalies)
    baseline = apply_thresholds(anomalies)
    events = load_events()
    gt = events.loc[events["severity"] >= validate.GT_SEVERITY_MIN, "date"].sort_values()

    comparison = validate.compare(compound, baseline, gt.reset_index(drop=True))
    sensitivity = validate.threshold_sensitivity(compound, gt.reset_index(drop=True))

    # Backend owns the plotting too; the UI just displays the saved PNGs.
    fig_cmp = validate.plot_comparison(
        compound, baseline, gt.reset_index(drop=True), FIGURES_DIR / "baseline_vs_compound.png"
    )
    fig_sens = validate.plot_sensitivity(sensitivity, FIGURES_DIR / "threshold_sensitivity.png")

    # Joined frame reused by the Explanation page.
    joined = (
        merged[["events", "n_events", "event_severity_sum"]]
        .join(features[["brent_return", "freight_wci_ffill", "event_severity_14"]])
        .join(anomalies)
        .join(compound)
    )

    return {
        "merged": merged,
        "features": features,
        "anomalies": anomalies,
        "compound": compound,
        "baseline": baseline,
        "events": events,
        "comparison": comparison,
        "sensitivity": sensitivity,
        "joined": joined,
        "fig_cmp": str(fig_cmp),
        "fig_sens": str(fig_sens),
    }


def page_timeline(data: dict[str, object]) -> None:
    """Timeline page: documented event log and the compound score over time."""
    st.header("Timeline")
    events = data["events"]
    st.subheader("Documented corridor events")
    st.dataframe(events[["date", "event", "category", "severity"]], use_container_width=True)
    st.subheader("Compound risk score over time")
    st.line_chart(data["compound"]["compound_score"])


def page_signals(data: dict[str, object]) -> None:
    """Signals page: per-signal anomaly scores and their raw features."""
    st.header("Signals")
    anomalies = data["anomalies"]
    st.subheader("Anomaly scores (robust z, clipped [-3, 3])")
    st.line_chart(anomalies[["anomaly_brent", "anomaly_freight", "anomaly_events"]])
    st.caption("Scores are computed in anomalies.py; this page only plots them.")
    st.subheader("Underlying features")
    st.line_chart(data["features"][["brent_return", "event_severity_14"]])
    st.line_chart(data["features"][["freight_wci_ffill"]])


def page_compound_vs_baseline(data: dict[str, object]) -> None:
    """Compound vs Baseline page: comparison figure, metrics and sensitivity."""
    st.header("Compound vs Baseline")
    comp = data["comparison"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Compound alert days", int(comp.loc["compound", "alert_days"]))
    c2.metric("Compound true positives", int(comp.loc["compound", "tp"]))
    c3.metric("Compound false positives", int(comp.loc["compound", "fp"]))

    st.image(data["fig_cmp"], use_container_width=True)
    st.subheader("Comparison metrics")
    st.dataframe(comp, use_container_width=True)
    st.subheader("Compound threshold sensitivity")
    st.image(data["fig_sens"], use_container_width=True)
    st.dataframe(data["sensitivity"], use_container_width=True)


def page_explanation(data: dict[str, object]) -> None:
    """Explanation page: traceable explanation for a chosen day."""
    st.header("Explanation")
    joined = data["joined"]
    dates = [d.date().isoformat() for d in joined.index]
    default_idx = int(joined["compound_score"].to_numpy().argmax())
    chosen = st.selectbox("Select a day", dates, index=default_idx)

    exp = explain_day(chosen, joined)
    st.text(exp.text)
    with st.expander("Audit trail (raw → anomalies → contributions → score)"):
        st.json(exp.trace)


def page_assumptions() -> None:
    """Assumptions page: render the assumptions register verbatim."""
    st.header("Assumptions & parameters")
    path = DOCS_DIR / "assumptions.md"
    if path.exists():
        st.markdown(path.read_text())
    else:
        st.warning("assumptions.md not found.")


def page_replay(data: dict[str, object]) -> None:
    """Replay page: step through the window day by day."""
    st.header("Replay")
    compound = data["compound"]
    dates = list(compound.index)
    idx = st.slider("Day", 0, len(dates) - 1, len(dates) - 1)
    current = compound.iloc[idx]
    st.metric(
        f"Risk on {dates[idx].date().isoformat()}",
        str(current["risk_level"]),
        f"{current['compound_score']:.2f}",
    )
    st.line_chart(compound["compound_score"].iloc[: idx + 1])
    events_today = data["merged"].iloc[idx]["events"]
    if events_today:
        st.info(f"Event: {events_today}")


def main() -> None:
    """Entry point: sidebar routing over the six pages."""
    st.set_page_config(page_title="EnergyGuardian AI", layout="wide")
    st.title("EnergyGuardian AI")
    st.caption("Compound disruption detection from weak public signals — visualization layer")

    data = load_backend()
    pages = {
        "Timeline": lambda: page_timeline(data),
        "Signals": lambda: page_signals(data),
        "Compound vs Baseline": lambda: page_compound_vs_baseline(data),
        "Explanation": lambda: page_explanation(data),
        "Assumptions": page_assumptions,
        "Replay": lambda: page_replay(data),
    }
    choice = st.sidebar.radio("Page", list(pages.keys()))
    pages[choice]()


if __name__ == "__main__":
    main()
