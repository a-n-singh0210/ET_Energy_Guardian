"""features.py — Module 3: reproducible engineered features.

Turns the merged raw frame (Module 2) into documented feature time series, one
row per calendar day. These are the *inputs* the anomaly engine (Module 4) will
later score — this module does NOT compute anomaly/z-scores itself.

Every feature is documented in ``FEATURE_DOCS`` and printed by the acceptance
check. Where a spec-suggested feature has no underlying public data, it is
omitted and the limitation is stated rather than fabricated.

Run standalone::

    python features.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ingestion import build_merged

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("features")

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
FEATURES_CSV = PROCESSED_DIR / "features.csv"

# Rolling window in days. Matches the anomaly engine's fixed 14-day window so
# features and their later anomaly scoring share a consistent horizon.
ROLLING_WINDOW = 14  # assumed

# One line of documentation per engineered feature (spec: "document every
# feature"). Printed by the acceptance check and kept next to the code.
FEATURE_DOCS: dict[str, str] = {
    "brent_return": "Brent daily close-to-close return (trading days; context signal).",
    "brent_volatility_14": "Rolling std of Brent daily returns over 14 trading days.",
    "brent_roll_return_14": "Brent 14-trading-day return (close_t / close_{t-14} - 1).",
    "freight_wci_ffill": "Drewry WCI composite level, forward-filled across the calendar (assumption: sparse weekly series carried forward between documented prints).",
    "freight_wci_ret": "Period-over-period return of the forward-filled WCI level (non-zero only when a new documented value arrives).",
    "n_events": "Count of corridor events recorded on the day (passthrough).",
    "event_severity_sum": "Sum of event severities recorded on the day (passthrough).",
    "event_freq_14": "Rolling 14-day count of corridor events (event frequency).",
    "event_severity_14": "Rolling 14-day sum of event severities (accumulated corridor pressure).",
    "carrier_suspension_flag": "1 if the day carries a carrier_suspension event, else 0 (carrier suspension indicator).",
}

# Spec-suggested features that have no underlying public data in scope. Stated,
# not fabricated (per docs/spec.md: "if data is unavailable, state the limitation").
UNAVAILABLE_FEATURES: dict[str, str] = {
    "insurance_premium_indicator": "No public war-risk insurance premium series was sourced; omitted rather than invented.",
    "transit_reduction_indicator": "No public Suez/Bab-el-Mandeb transit-count series was sourced; the freight WCI features act as the shipping-disruption proxy instead.",
}


def build_features(merged: pd.DataFrame) -> pd.DataFrame:
    """Compute the engineered feature frame from the merged raw frame.

    Args:
        merged: Output of ``ingestion.build_merged`` (daily calendar index with
            ``brent_close``, ``wci_composite_usd_per_40ft``, ``n_events``,
            ``event_severity_sum``, ``event_categories`` columns).

    Returns:
        DataFrame indexed by daily ``date`` with the columns listed in
        ``FEATURE_DOCS``.

    Raises:
        KeyError: If a required source column is missing from ``merged``.
    """
    required = {
        "brent_close",
        "wci_composite_usd_per_40ft",
        "n_events",
        "event_severity_sum",
        "event_categories",
    }
    missing = required - set(merged.columns)
    if missing:
        raise KeyError(f"merged frame is missing required columns: {sorted(missing)}")

    feats = pd.DataFrame(index=merged.index)

    # --- Brent context features (computed on trading days, realigned) --------
    brent = merged["brent_close"].dropna()
    brent_return = brent.pct_change()
    brent_vol = brent_return.rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).std()
    brent_roll_return = brent.pct_change(periods=ROLLING_WINDOW)
    feats["brent_return"] = brent_return.reindex(feats.index)
    feats["brent_volatility_14"] = brent_vol.reindex(feats.index)
    feats["brent_roll_return_14"] = brent_roll_return.reindex(feats.index)

    # --- Freight proxy features (sparse; forward-filled level) ---------------
    wci_ffill = merged["wci_composite_usd_per_40ft"].ffill()
    feats["freight_wci_ffill"] = wci_ffill
    feats["freight_wci_ret"] = wci_ffill.pct_change()

    # --- Event features ------------------------------------------------------
    feats["n_events"] = merged["n_events"].astype(int)
    feats["event_severity_sum"] = merged["event_severity_sum"].astype(float)
    feats["event_freq_14"] = (
        merged["n_events"].rolling(ROLLING_WINDOW, min_periods=1).sum().astype(float)
    )
    feats["event_severity_14"] = (
        merged["event_severity_sum"].rolling(ROLLING_WINDOW, min_periods=1).sum().astype(float)
    )
    feats["carrier_suspension_flag"] = (
        merged["event_categories"].str.contains("carrier_suspension").astype(int)
    )

    logger.info(
        "Built %d features over %d calendar days.", feats.shape[1], feats.shape[0]
    )
    return feats


def build_and_save(save: bool = True) -> pd.DataFrame:
    """Run Module 3 end to end: merge → features (and optionally save).

    Args:
        save: If True, write the feature frame to ``data/processed/features.csv``.

    Returns:
        The engineered feature DataFrame.
    """
    merged = build_merged(save=False)
    feats = build_features(merged)
    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        feats.to_csv(FEATURES_CSV, index=True)
        logger.info("Saved features to %s", FEATURES_CSV)
    return feats


if __name__ == "__main__":
    df = build_and_save(save=True)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)

    print("=" * 90)
    print(f"MODULE 3 ACCEPTANCE — engineered features  |  shape = {df.shape}")
    print("=" * 90)

    print("\nFeature documentation:")
    for name, doc in FEATURE_DOCS.items():
        print(f"  - {name}: {doc}")

    print("\nUnavailable (stated, not fabricated):")
    for name, why in UNAVAILABLE_FEATURES.items():
        print(f"  - {name}: {why}")

    print("\nNon-null counts:")
    print(df.notna().sum().to_string())

    print("\nHead (first 5 days):")
    print(df.head(5).to_string())

    print("\nEvent-day rows (engineered features on days with corridor events):")
    print(df[df["n_events"] > 0].to_string())
