"""baseline.py — Module 6: the independent threshold engine (fair baseline).

The baseline is the comparison point for the compound model. It treats every
signal **independently** and raises an alert whenever **any single** signal's
anomaly meets its threshold. By construction it cannot see interactions between
signals — that blind spot is what Module 7 measures against the compound model.

The baseline is deliberately *fair*, not weakened:
* it reads the exact same anomaly scores the compound model uses;
* it uses a standard notable-anomaly threshold (robust z ≥ 2.0), applied
  uniformly to every signal;
* thresholds are configurable in ``BASELINE_THRESHOLDS``.

Alert direction is **elevation** (aᵢ ≥ threshold), consistent with the system's
elevation-based notion of risk (more corridor events / higher freight / an
upward price shock). A signal whose robust-z simply never reaches the threshold
(e.g. the mild freight anomaly) is a genuine property of the data, not a
hobbled baseline — lower its threshold to make it fire.

Run standalone::

    python baseline.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("baseline")

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
BASELINE_CSV = PROCESSED_DIR / "baseline.csv"

# Independent per-signal alert thresholds on the robust-z anomaly score.
# z = 2.0 is a standard notable-anomaly level, applied uniformly (fair, not
# weakened). Configurable.
BASELINE_THRESHOLDS: dict[str, float] = {
    "brent": 2.0,    # assumed
    "freight": 2.0,  # assumed
    "events": 2.0,   # assumed
}


class BaselineError(RuntimeError):
    """Raised when required anomaly inputs are missing."""


def apply_thresholds(
    anomalies: pd.DataFrame,
    thresholds: dict[str, float] = BASELINE_THRESHOLDS,
) -> pd.DataFrame:
    """Apply independent per-signal thresholds and derive the baseline alert.

    Args:
        anomalies: Frame with an ``anomaly_<signal>`` column per signal in
            ``thresholds``.
        thresholds: Mapping ``signal -> threshold`` on the anomaly score.

    Returns:
        A DataFrame indexed by ``date`` with:
        * ``exceed_<signal>`` — bool, that signal alone met its threshold.
        * ``baseline_alert`` — bool, ANY signal met its threshold.
        * ``triggered_signals`` — comma-joined names of the triggering signals.

    Raises:
        BaselineError: If a required ``anomaly_<signal>`` column is missing.
    """
    if not thresholds:
        raise BaselineError("No baseline thresholds configured.")

    out = pd.DataFrame(index=anomalies.index)
    exceed_cols: list[str] = []
    for signal, threshold in thresholds.items():
        col = f"anomaly_{signal}"
        if col not in anomalies.columns:
            raise BaselineError(f"Expected anomaly column '{col}' not found.")
        exceed = anomalies[col] >= threshold
        out[f"exceed_{signal}"] = exceed
        exceed_cols.append(f"exceed_{signal}")

    out["baseline_alert"] = out[exceed_cols].any(axis=1)
    out["triggered_signals"] = out[exceed_cols].apply(
        lambda row: ",".join(s for s in thresholds if row[f"exceed_{s}"]), axis=1
    )

    logger.info(
        "Baseline alerts on %d of %d days (thresholds=%s).",
        int(out["baseline_alert"].sum()),
        len(out),
        thresholds,
    )
    return out


def _load_anomalies() -> pd.DataFrame:
    """Build anomaly scores fresh via the Module 4 pipeline (no stale files)."""
    from anomalies import build_and_save as build_anomalies

    return build_anomalies(save=False)


def build_and_save(save: bool = True) -> pd.DataFrame:
    """Run Module 6 end to end: anomalies -> baseline alerts (optionally save).

    Args:
        save: If True, write to ``data/processed/baseline.csv``.

    Returns:
        The baseline-annotated DataFrame.
    """
    anomalies = _load_anomalies()
    baseline = apply_thresholds(anomalies)
    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        baseline.to_csv(BASELINE_CSV, index=True)
        logger.info("Saved baseline results to %s", BASELINE_CSV)
    return baseline


if __name__ == "__main__":
    anomalies = _load_anomalies()
    df = apply_thresholds(anomalies)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(BASELINE_CSV, index=True)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print("=" * 80)
    print("MODULE 6 ACCEPTANCE — independent baseline threshold engine")
    print("=" * 80)
    print(f"\nThresholds (elevation, aᵢ ≥ t; all # assumed): {BASELINE_THRESHOLDS}")
    print(f"Total baseline alert days: {int(df['baseline_alert'].sum())} of {len(df)}")

    print("\nBaseline alerts (days where any single signal crossed its threshold):")
    alerts = df[df["baseline_alert"]].copy()
    show = alerts.join(anomalies)  # show the anomaly values alongside the flags
    cols = ["anomaly_brent", "anomaly_freight", "anomaly_events", "triggered_signals"]
    print(show[cols].round(3).to_string())
