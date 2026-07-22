"""validate.py — Module 7: validation of compound vs baseline.

Computes lead time, false positives, false negatives, a baseline-vs-compound
comparison, and a threshold-sensitivity sweep, then saves figures. All metrics
are derived from real alerts and documented events — nothing is fabricated.

Ground truth (documented, tagged as assumptions — see docs/assumptions.md):
* **Disruption events to detect** = corridor events with severity ≥ 4 from
  ``data/red_sea_events.csv`` (the materially disruptive incidents).
* **Systemic onset** = 2023-12-15, the documented day major carriers began
  suspending Red Sea transit (used for the headline lead-time metric).
* A detection counts if a method alerts within ±3 days of a ground-truth event;
  a false positive is an alert day not within ±3 days of any such event.

Both methods read the identical anomaly scores, so the comparison is fair.

Run standalone::

    python validate.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: save figures without a display
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("validate")

ROOT = Path(__file__).resolve().parent
FIGURES_DIR = ROOT / "figures"

# --------------------------------------------------------------------------- #
# Ground-truth / evaluation parameters (assumed; mirrored in assumptions.md)
# --------------------------------------------------------------------------- #
GT_SEVERITY_MIN = 4          # assumed — severity threshold for "disruption event"
DETECTION_TOL_DAYS = 3       # assumed — ± window for counting a detection
LEAD_LOOKBACK_DAYS = 30      # assumed — how far before onset an alert may lead
SYSTEMIC_ONSET = "2023-12-15"  # documented — carrier suspensions begin
COMPOUND_ALERT_THRESHOLD = 2.5  # assumed — = HIGH risk bound in compound.py

# Grids for threshold sensitivity.
COMPOUND_GRID = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
BASELINE_GRID = (1.0, 1.5, 2.0, 2.5, 3.0)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    """Build the compound, baseline and anomaly frames plus ground-truth events.

    Returns:
        Tuple ``(compound, baseline, anomalies, gt_event_dates)`` where the
        first three are indexed by ``date`` and the last is a Series of
        documented disruption-event dates (severity ≥ GT_SEVERITY_MIN).
    """
    from anomalies import build_and_save as build_anomalies
    from baseline import apply_thresholds
    from compound import compute_compound
    from ingestion import load_events

    anomalies = build_anomalies(save=False)
    compound = compute_compound(anomalies)
    baseline = apply_thresholds(anomalies)

    events = load_events()
    gt = events.loc[events["severity"] >= GT_SEVERITY_MIN, "date"].sort_values()
    return compound, baseline, anomalies, gt.reset_index(drop=True)


def compound_alert_dates(
    compound: pd.DataFrame, threshold: float = COMPOUND_ALERT_THRESHOLD
) -> pd.DatetimeIndex:
    """Dates where the compound score meets an alert threshold.

    Args:
        compound: Compound frame with ``compound_score``.
        threshold: Alert threshold on the compound score.

    Returns:
        DatetimeIndex of alert dates.
    """
    return compound.index[compound["compound_score"] >= threshold]


def baseline_alert_dates(baseline: pd.DataFrame) -> pd.DatetimeIndex:
    """Dates where the independent baseline raised an alert.

    Args:
        baseline: Baseline frame with ``baseline_alert``.

    Returns:
        DatetimeIndex of alert dates.
    """
    return baseline.index[baseline["baseline_alert"].astype(bool)]


def lead_time_days(
    alert_dates: pd.DatetimeIndex,
    onset: str = SYSTEMIC_ONSET,
    lookback: int = LEAD_LOOKBACK_DAYS,
) -> float | None:
    """Lead time (days) between the earliest pre-onset alert and the onset.

    Args:
        alert_dates: Dates a method alerted.
        onset: Documented systemic onset date.
        lookback: How many days before onset an alert may count.

    Returns:
        Positive lead in days, or ``None`` if the method did not alert in the
        window ``[onset - lookback, onset]``.
    """
    onset_ts = pd.Timestamp(onset)
    window_start = onset_ts - pd.Timedelta(days=lookback)
    candidates = alert_dates[(alert_dates >= window_start) & (alert_dates <= onset_ts)]
    if len(candidates) == 0:
        return None
    return float((onset_ts - candidates.min()).days)


def detection_metrics(
    alert_dates: pd.DatetimeIndex,
    gt_dates: pd.Series,
    tol: int = DETECTION_TOL_DAYS,
) -> dict[str, int]:
    """Compute TP, FN and FP against documented ground-truth events.

    Args:
        alert_dates: Dates a method alerted.
        gt_dates: Documented disruption-event dates.
        tol: ± day tolerance for matching an alert to an event.

    Returns:
        Dict with ``tp``, ``fn`` (over the event set) and ``fp`` (alert days not
        within ``tol`` of any event).
    """
    tol_td = pd.Timedelta(days=tol)
    detected = 0
    for event in gt_dates:
        near = alert_dates[(alert_dates >= event - tol_td) & (alert_dates <= event + tol_td)]
        if len(near) > 0:
            detected += 1
    fn = len(gt_dates) - detected

    fp = 0
    for a in alert_dates:
        near_event = gt_dates[(gt_dates >= a - tol_td) & (gt_dates <= a + tol_td)]
        if len(near_event) == 0:
            fp += 1

    return {"tp": detected, "fn": fn, "fp": fp}


def compare(compound: pd.DataFrame, baseline: pd.DataFrame, gt: pd.Series) -> pd.DataFrame:
    """Build the baseline-vs-compound comparison table.

    Args:
        compound: Compound frame.
        baseline: Baseline frame.
        gt: Ground-truth event dates.

    Returns:
        DataFrame with one row per method and columns ``alert_days``,
        ``lead_time_days``, ``tp``, ``fn``, ``fp``.
    """
    rows = []
    for name, dates in (
        ("baseline", baseline_alert_dates(baseline)),
        ("compound", compound_alert_dates(compound)),
    ):
        m = detection_metrics(dates, gt)
        rows.append(
            {
                "method": name,
                "alert_days": len(dates),
                "lead_time_days": lead_time_days(dates),
                "tp": m["tp"],
                "fn": m["fn"],
                "fp": m["fp"],
            }
        )
    return pd.DataFrame(rows).set_index("method")


def threshold_sensitivity(
    compound: pd.DataFrame, gt: pd.Series, grid: tuple[float, ...] = COMPOUND_GRID
) -> pd.DataFrame:
    """Sweep the compound alert threshold and report detection metrics.

    Args:
        compound: Compound frame.
        gt: Ground-truth event dates.
        grid: Compound-score thresholds to evaluate.

    Returns:
        DataFrame with ``threshold``, ``alert_days``, ``tp``, ``fn``, ``fp``,
        ``lead_time_days``.
    """
    rows = []
    for thr in grid:
        dates = compound_alert_dates(compound, threshold=thr)
        m = detection_metrics(dates, gt)
        rows.append(
            {
                "threshold": thr,
                "alert_days": len(dates),
                "tp": m["tp"],
                "fn": m["fn"],
                "fp": m["fp"],
                "lead_time_days": lead_time_days(dates),
            }
        )
    return pd.DataFrame(rows)


def baseline_threshold_sensitivity(
    anomalies: pd.DataFrame, gt: pd.Series, grid: tuple[float, ...] = BASELINE_GRID
) -> pd.DataFrame:
    """Sweep the uniform baseline z-threshold and report detection metrics.

    Args:
        anomalies: Anomaly-score frame.
        gt: Ground-truth event dates.
        grid: Uniform robust-z thresholds to evaluate.

    Returns:
        DataFrame with ``threshold``, ``alert_days``, ``tp``, ``fn``, ``fp``.
    """
    from baseline import apply_thresholds

    signals = [c.replace("anomaly_", "") for c in anomalies.columns if c.startswith("anomaly_")]
    rows = []
    for thr in grid:
        bl = apply_thresholds(anomalies, thresholds={s: thr for s in signals})
        dates = baseline_alert_dates(bl)
        m = detection_metrics(dates, gt)
        rows.append(
            {"threshold": thr, "alert_days": len(dates), "tp": m["tp"], "fn": m["fn"], "fp": m["fp"]}
        )
    return pd.DataFrame(rows)


def plot_comparison(
    compound: pd.DataFrame,
    baseline: pd.DataFrame,
    gt: pd.Series,
    save_path: Path,
) -> Path:
    """Plot the compound score with alert markers and ground-truth events.

    Args:
        compound: Compound frame.
        baseline: Baseline frame.
        gt: Ground-truth event dates.
        save_path: PNG destination.

    Returns:
        The path written.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(compound.index, compound["compound_score"], color="#1f4e79", label="Compound score")
    ax.axhline(COMPOUND_ALERT_THRESHOLD, color="#c0392b", ls="--", lw=1,
               label=f"Compound alert ({COMPOUND_ALERT_THRESHOLD})")

    c_dates = compound_alert_dates(compound)
    b_dates = baseline_alert_dates(baseline)
    ax.scatter(c_dates, compound.loc[c_dates, "compound_score"], marker="o",
               facecolors="none", edgecolors="#c0392b", s=110, label="Compound alert", zorder=4)
    ax.scatter(b_dates, compound.loc[b_dates, "compound_score"], marker="v",
               color="#e67e22", s=70, label="Baseline alert", zorder=3)

    for i, ev in enumerate(gt):
        ax.axvline(ev, color="grey", ls=":", lw=0.8, label="GT disruption event" if i == 0 else None)
    ax.axvline(pd.Timestamp(SYSTEMIC_ONSET), color="black", lw=1.2,
               label=f"Systemic onset {SYSTEMIC_ONSET}")

    ax.set_title("EnergyGuardian — compound vs baseline against documented disruptions")
    ax.set_xlabel("Date")
    ax.set_ylabel("Compound score")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=120)
    plt.close(fig)
    logger.info("Saved %s", save_path)
    return save_path


def plot_sensitivity(sensitivity: pd.DataFrame, save_path: Path) -> Path:
    """Plot detection metrics across the compound threshold grid.

    Args:
        sensitivity: Output of :func:`threshold_sensitivity`.
        save_path: PNG destination.

    Returns:
        The path written.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(sensitivity["threshold"], sensitivity["tp"], marker="o", color="#27ae60", label="True positives")
    ax.plot(sensitivity["threshold"], sensitivity["fp"], marker="s", color="#c0392b", label="False positives")
    ax.plot(sensitivity["threshold"], sensitivity["fn"], marker="^", color="#e67e22", label="False negatives")
    ax.plot(sensitivity["threshold"], sensitivity["alert_days"], marker="d", color="#1f4e79",
            ls="--", label="Alert days")
    ax.set_title("Compound threshold sensitivity")
    ax.set_xlabel("Compound alert threshold")
    ax.set_ylabel("Count")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=120)
    plt.close(fig)
    logger.info("Saved %s", save_path)
    return save_path


def run_validation() -> dict[str, object]:
    """Run the full Module 7 pipeline and save figures.

    Returns:
        Dict with the comparison table and both sensitivity tables.
    """
    compound, baseline, anomalies, gt = load_inputs()
    comparison = compare(compound, baseline, gt)
    sens_compound = threshold_sensitivity(compound, gt)
    sens_baseline = baseline_threshold_sensitivity(anomalies, gt)

    plot_comparison(compound, baseline, gt, FIGURES_DIR / "baseline_vs_compound.png")
    plot_sensitivity(sens_compound, FIGURES_DIR / "threshold_sensitivity.png")

    return {
        "gt_events": gt,
        "comparison": comparison,
        "sensitivity_compound": sens_compound,
        "sensitivity_baseline": sens_baseline,
    }


if __name__ == "__main__":
    results = run_validation()
    pd.set_option("display.width", 200)

    print("=" * 82)
    print("MODULE 7 ACCEPTANCE — validation metrics (baseline vs compound)")
    print("=" * 82)
    print(f"\nGround truth: {len(results['gt_events'])} documented disruption events "
          f"(severity >= {GT_SEVERITY_MIN}); systemic onset {SYSTEMIC_ONSET}.")
    print(f"Detection tolerance ±{DETECTION_TOL_DAYS}d; compound alert threshold "
          f"{COMPOUND_ALERT_THRESHOLD}.")

    print("\nComparison (lead time in days; tp/fn over events; fp = spurious alert days):")
    print(results["comparison"].to_string())

    print("\nCompound threshold sensitivity:")
    print(results["sensitivity_compound"].to_string(index=False))

    print("\nBaseline threshold sensitivity (uniform z):")
    print(results["sensitivity_baseline"].to_string(index=False))

    print(f"\nFigures saved to: {FIGURES_DIR}")
