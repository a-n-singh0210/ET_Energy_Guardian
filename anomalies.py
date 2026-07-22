"""anomalies.py — Module 4: independent per-signal anomaly scores.

Scores a small set of heterogeneous signals independently using **robust
z-scores** over a rolling 14-day window, clipped to [-3, 3]. Robust statistics
(median and MAD) are used instead of mean/std so a single spike does not inflate
its own baseline.

Every transformation is recorded in ``ANOMALY_DOCS`` and printed by the
acceptance check. No machine learning is used.

Transformation, per signal:
    1. robust z  =  (x - rolling_median) / (1.4826 * rolling_MAD)
    2. windows with zero dispersion (MAD == 0) -> z = 0 (no anomaly signal)
    3. clip to [-3, 3]
    4. warmup rows (fewer than 14 observations) -> 0.0 (no baseline yet)

Run standalone::

    python anomalies.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("anomalies")

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
ANOMALIES_CSV = PROCESSED_DIR / "anomalies.csv"

ROLLING_WINDOW = 14  # fixed by spec
CLIP = 3.0  # fixed by spec
MAD_TO_STD = 1.4826  # scales MAD to a std-consistent estimator for normal data

# Signals to score, mapped to their feature column and how the window is counted.
# "obs"  -> 14 trading observations (Brent trades on business days only)
# "cal"  -> 14 calendar days (event/freight features are defined daily)
ANOMALY_SIGNALS: dict[str, dict[str, str]] = {
    "brent": {"feature": "brent_return", "window_basis": "obs"},
    "freight": {"feature": "freight_wci_ffill", "window_basis": "cal"},
    "events": {"feature": "event_severity_14", "window_basis": "cal"},
}

ANOMALY_DOCS: dict[str, str] = {
    "anomaly_brent": "Robust z-score of Brent daily return over 14 trading days (context price shock).",
    "anomaly_freight": "Robust z-score of the forward-filled Drewry WCI level over 14 calendar days (freight-rate dislocation).",
    "anomaly_events": "Robust z-score of the rolling 14-day event-severity sum over 14 calendar days (corridor pressure).",
}


def robust_zscore(series: pd.Series, window: int = ROLLING_WINDOW) -> pd.Series:
    """Compute a rolling robust z-score of a series.

    robust z = (x - median) / (1.4826 * MAD), where both the median and the MAD
    (median absolute deviation) are computed within each trailing window.

    Args:
        series: Numeric series (already restricted to its natural observations,
            e.g. trading days for Brent).
        window: Rolling-window length in rows.

    Returns:
        Series of robust z-scores aligned to ``series``. Windows with zero MAD
        yield 0.0; warmup rows (fewer than ``window`` observations) are NaN and
        are zero-filled by the caller.

    Raises:
        ValueError: If ``window`` < 2.
    """
    if window < 2:
        raise ValueError(f"window must be >= 2, got {window}.")

    med = series.rolling(window, min_periods=window).median()

    def _mad(vals: np.ndarray) -> float:
        return float(np.median(np.abs(vals - np.median(vals))))

    mad = series.rolling(window, min_periods=window).apply(_mad, raw=True)
    scale = MAD_TO_STD * mad

    z = (series - med) / scale
    # Zero-dispersion windows are not anomalous: define their z as 0.
    z = z.where(scale != 0, other=0.0)
    return z


def score_signal(feature_series: pd.Series, window: int = ROLLING_WINDOW) -> pd.Series:
    """Score one signal: robust z-score then clip to [-CLIP, CLIP].

    Args:
        feature_series: The feature values on their natural observation index.
        window: Rolling-window length.

    Returns:
        Clipped robust z-score series.
    """
    z = robust_zscore(feature_series, window=window)
    return z.clip(lower=-CLIP, upper=CLIP)


def compute_anomalies(features: pd.DataFrame) -> pd.DataFrame:
    """Compute independent anomaly scores for all configured signals.

    Args:
        features: Engineered feature frame (Module 3) indexed by daily ``date``.

    Returns:
        DataFrame indexed by daily ``date`` with an ``anomaly_<signal>`` column
        per configured signal, in [-3, 3]. Warmup/undefined rows are 0.0.

    Raises:
        KeyError: If a configured feature column is missing.
    """
    out = pd.DataFrame(index=features.index)

    for name, spec in ANOMALY_SIGNALS.items():
        feature = spec["feature"]
        if feature not in features.columns:
            raise KeyError(f"anomaly signal '{name}' needs missing feature '{feature}'.")

        raw = features[feature]
        if spec["window_basis"] == "obs":
            # Score on the natural (non-NaN) observations, then realign.
            natural = raw.dropna()
            scored = score_signal(natural).reindex(features.index)
        else:
            scored = score_signal(raw)

        out[f"anomaly_{name}"] = scored.fillna(0.0)
        logger.info(
            "Signal '%s' (%s): min=%.2f max=%.2f non-zero days=%d",
            name,
            feature,
            float(out[f"anomaly_{name}"].min()),
            float(out[f"anomaly_{name}"].max()),
            int((out[f"anomaly_{name}"] != 0).sum()),
        )
    return out


def build_and_save(save: bool = True) -> pd.DataFrame:
    """Run Module 4 end to end: features -> anomaly scores (optionally save).

    Args:
        save: If True, write anomalies to ``data/processed/anomalies.csv``.

    Returns:
        The anomaly-score DataFrame.
    """
    features = _load_features()
    anomalies = compute_anomalies(features)
    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        anomalies.to_csv(ANOMALIES_CSV, index=True)
        logger.info("Saved anomalies to %s", ANOMALIES_CSV)
    return anomalies


def _load_features() -> pd.DataFrame:
    """Build the engineered features fresh (no stale intermediate files)."""
    from features import build_and_save as build_features

    return build_features(save=False)


if __name__ == "__main__":
    df = build_and_save(save=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print("=" * 84)
    print(f"MODULE 4 ACCEPTANCE — anomaly scores  |  shape = {df.shape}")
    print("=" * 84)

    print("\nTransformation (per signal): robust z over 14d -> MAD==0 => 0 -> clip [-3,3] -> warmup 0")
    print("\nSignal documentation:")
    for name, doc in ANOMALY_DOCS.items():
        print(f"  - {name}: {doc}")

    print("\nSummary statistics:")
    print(df.describe().round(3).to_string())

    print("\nRows where any signal is anomalous (|score| >= 1):")
    flagged = df[(df.abs() >= 1).any(axis=1)]
    print(flagged.round(3).to_string())
