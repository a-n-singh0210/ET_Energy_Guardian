"""ingestion.py — Module 2: load, validate and merge the raw public data.

Loads the three Module 1 data files (Red Sea events, freight proxy, Brent
context), validates each against its expected schema, and merges them by date
onto a continuous daily calendar covering the analysis window.

This module performs **no feature engineering** and **no anomaly maths** — only
loading, validation and a light aggregation needed to place many-per-day events
onto a one-row-per-day frame. Missing values are left as-is (not filled); how to
align the sparse freight series is a modelling decision for later modules.

Run standalone::

    python ingestion.py
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ingestion")

# Paths are resolved relative to this file so the module runs from anywhere.
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
EVENTS_CSV = DATA_DIR / "red_sea_events.csv"
FREIGHT_CSV = DATA_DIR / "freight_proxy.csv"
BRENT_CSV = DATA_DIR / "brent.csv"
PROCESSED_DIR = DATA_DIR / "processed"
MERGED_CSV = PROCESSED_DIR / "merged.csv"

# Analysis window (inclusive) — the daily calendar backbone for the merge.
WINDOW_START = "2023-10-01"
WINDOW_END = "2024-03-31"

# Expected columns per source file.
EVENTS_COLUMNS = {"date", "event", "category", "severity", "source_id"}
FREIGHT_COLUMNS = {"date", "wci_composite_usd_per_40ft", "source_id", "note"}
BRENT_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


class IngestionError(RuntimeError):
    """Raised when a data file is missing, malformed, or fails validation."""


def _require_file(path: Path) -> None:
    """Raise IngestionError if a required file is absent.

    Args:
        path: File that must exist.

    Raises:
        IngestionError: If the file does not exist.
    """
    if not path.exists():
        raise IngestionError(f"Required data file not found: {path}")


def _require_columns(df: pd.DataFrame, expected: set[str], name: str) -> None:
    """Raise IngestionError if any expected column is missing.

    Args:
        df: Loaded DataFrame.
        expected: Column names that must be present.
        name: Human-readable file name for error messages.

    Raises:
        IngestionError: If a column is missing.
    """
    missing = expected - set(df.columns)
    if missing:
        raise IngestionError(f"{name} is missing required columns: {sorted(missing)}")


def load_events(path: Path = EVENTS_CSV) -> pd.DataFrame:
    """Load and validate the Red Sea event log.

    Args:
        path: Path to ``red_sea_events.csv``.

    Returns:
        DataFrame with a parsed ``date`` column and numeric ``severity``.

    Raises:
        IngestionError: If the file is missing, a column is absent, dates do not
            parse, or severities are out of the 1-5 range.
    """
    _require_file(path)
    df = pd.read_csv(path)
    _require_columns(df, EVENTS_COLUMNS, path.name)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise IngestionError(f"{path.name} contains unparseable dates.")

    df["severity"] = pd.to_numeric(df["severity"], errors="coerce")
    if df["severity"].isna().any():
        raise IngestionError(f"{path.name} contains non-numeric severity values.")
    if not df["severity"].between(1, 5).all():
        raise IngestionError(f"{path.name} has severity values outside 1-5.")

    logger.info("Loaded %d events from %s", len(df), path.name)
    return df.sort_values("date").reset_index(drop=True)


def load_freight(path: Path = FREIGHT_CSV) -> pd.DataFrame:
    """Load and validate the freight proxy (Drewry WCI composite).

    Args:
        path: Path to ``freight_proxy.csv``.

    Returns:
        DataFrame with a parsed ``date`` and numeric freight value.

    Raises:
        IngestionError: If the file is missing, a column is absent, dates do not
            parse, or any freight value is not positive.
    """
    _require_file(path)
    df = pd.read_csv(path)
    _require_columns(df, FREIGHT_COLUMNS, path.name)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise IngestionError(f"{path.name} contains unparseable dates.")

    df["wci_composite_usd_per_40ft"] = pd.to_numeric(
        df["wci_composite_usd_per_40ft"], errors="coerce"
    )
    if df["wci_composite_usd_per_40ft"].isna().any():
        raise IngestionError(f"{path.name} contains non-numeric freight values.")
    if not (df["wci_composite_usd_per_40ft"] > 0).all():
        raise IngestionError(f"{path.name} has non-positive freight values.")

    logger.info("Loaded %d freight observations from %s", len(df), path.name)
    return df.sort_values("date").reset_index(drop=True)


def load_brent(path: Path = BRENT_CSV) -> pd.DataFrame:
    """Load and validate the Brent crude context prices.

    Args:
        path: Path to ``brent.csv``.

    Returns:
        DataFrame with a parsed ``date`` and numeric ``close``.

    Raises:
        IngestionError: If the file is missing, a column is absent, dates do not
            parse, or any close price is not positive.
    """
    _require_file(path)
    df = pd.read_csv(path)
    _require_columns(df, BRENT_COLUMNS, path.name)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise IngestionError(f"{path.name} contains unparseable dates.")

    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    if df["close"].isna().any() or not (df["close"] > 0).all():
        raise IngestionError(f"{path.name} has missing or non-positive close prices.")

    logger.info("Loaded %d Brent rows from %s", len(df), path.name)
    return df.sort_values("date").reset_index(drop=True)


def _aggregate_events(events: pd.DataFrame) -> pd.DataFrame:
    """Collapse the many-per-day event log to one row per day.

    This is aggregation for the merge only (counts and joins) — it deliberately
    does not derive indicators or scores (those belong to feature engineering).

    Args:
        events: Validated event DataFrame.

    Returns:
        DataFrame indexed by ``date`` with ``n_events``, ``event_severity_sum``,
        ``event_severity_max``, ``event_categories`` and ``events`` columns.
    """
    grouped = events.groupby("date").agg(
        n_events=("event", "count"),
        event_severity_sum=("severity", "sum"),
        event_severity_max=("severity", "max"),
        event_categories=("category", lambda s: "|".join(sorted(set(s)))),
        events=("event", lambda s: " | ".join(s)),
    )
    return grouped


def merge_sources(
    events: pd.DataFrame,
    freight: pd.DataFrame,
    brent: pd.DataFrame,
    start: str = WINDOW_START,
    end: str = WINDOW_END,
) -> pd.DataFrame:
    """Merge the three sources by date onto a continuous daily calendar.

    Args:
        events: Validated event DataFrame.
        freight: Validated freight DataFrame.
        brent: Validated Brent DataFrame.
        start: Inclusive window start (``YYYY-MM-DD``).
        end: Inclusive window end (``YYYY-MM-DD``).

    Returns:
        DataFrame indexed by daily ``date`` with Brent context, freight proxy,
        and aggregated event columns. Event count/severity columns are
        zero-filled on non-event days; freight and Brent values are left as NaN
        where no observation exists (no fabricated fills).
    """
    calendar = pd.date_range(start=start, end=end, freq="D", name="date")
    merged = pd.DataFrame(index=calendar)

    # Brent context (trading days only; NaN on weekends/holidays).
    brent_indexed = brent.set_index("date")[["close", "volume"]]
    merged = merged.join(brent_indexed.rename(columns={"close": "brent_close", "volume": "brent_volume"}))

    # Freight proxy (sparse; left as NaN between documented observations).
    freight_indexed = freight.set_index("date")[["wci_composite_usd_per_40ft"]]
    merged = merged.join(freight_indexed)

    # Aggregated events (zero-filled on non-event days).
    events_agg = _aggregate_events(events)
    merged = merged.join(events_agg)
    merged["n_events"] = merged["n_events"].fillna(0).astype(int)
    merged["event_severity_sum"] = merged["event_severity_sum"].fillna(0.0)
    merged["event_severity_max"] = merged["event_severity_max"].fillna(0.0)
    merged["event_categories"] = merged["event_categories"].fillna("")
    merged["events"] = merged["events"].fillna("")

    logger.info(
        "Merged onto %d calendar days: %d Brent, %d freight, %d event-days.",
        len(merged),
        int(merged["brent_close"].notna().sum()),
        int(merged["wci_composite_usd_per_40ft"].notna().sum()),
        int((merged["n_events"] > 0).sum()),
    )
    return merged


def build_merged(save: bool = True) -> pd.DataFrame:
    """Run the full Module 2 pipeline: load, validate, merge (and optionally save).

    Args:
        save: If True, write the merged frame to ``data/processed/merged.csv``.

    Returns:
        The merged DataFrame indexed by daily ``date``.
    """
    events = load_events()
    freight = load_freight()
    brent = load_brent()
    merged = merge_sources(events, freight, brent)

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        merged.to_csv(MERGED_CSV, index=True)
        logger.info("Saved merged frame to %s", MERGED_CSV)
    return merged


if __name__ == "__main__":
    df = build_merged(save=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print("=" * 78)
    print(f"MODULE 2 ACCEPTANCE — merged dataframe  |  shape = {df.shape}")
    print("=" * 78)
    print("\nDtypes:")
    print(df.dtypes.to_string())
    print("\nNon-null counts:")
    print(df.notna().sum().to_string())
    print("\nHead (first 8 calendar days):")
    print(df.head(8).to_string())
    print("\nAll rows carrying an event or a freight observation:")
    signal_rows = df[(df["n_events"] > 0) | (df["wci_composite_usd_per_40ft"].notna())]
    print(signal_rows.to_string())
