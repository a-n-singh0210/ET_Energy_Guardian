"""compound.py — Module 5: the compound risk model (the innovation).

Implements the fixed model, applied per day:

    Risk(t) = Σ_i w_i · a_i(t)   +   λ · Σ_{i<j} a_i⁺(t) · a_j⁺(t)

where a_i are the signed anomaly scores (Module 4) in [-3, 3].

Modeling choice (approved, see docs/assumptions.md):
* The **linear term** uses the *signed* anomalies, so an unusually low signal
  reduces its linear contribution.
* The **interaction term** uses the *positive part, normalized by the clip
  bound*:  a_i⁺ = max(a_i, 0) / 3  ∈ [0, 1].  Interaction therefore represents
  the **co-elevation** of risk indicators, not co-depression, and λ has a
  stable interpretation on a [0,1]×[0,1] product.

All parameters (w_i, λ) appear once, below, tagged `# assumed` / `# estimated`,
and are mirrored in docs/assumptions.md. The layer returns every signal
contribution, every interaction contribution, the interaction matrix, the final
score and a risk level. No hidden calculations.

Run standalone::

    python compound.py
"""

from __future__ import annotations

import logging
from itertools import combinations
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("compound")

ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = ROOT / "data" / "processed"
COMPOUND_CSV = PROCESSED_DIR / "compound.csv"

# --------------------------------------------------------------------------- #
# MODEL PARAMETERS (appear once; mirrored in docs/assumptions.md)
# --------------------------------------------------------------------------- #
WEIGHTS: dict[str, float] = {
    "brent": 1.0,    # assumed — equal weighting; no basis to prefer one signal
    "freight": 1.0,  # assumed
    "events": 1.0,   # assumed
}
LAMBDA: float = 1.5  # assumed — interaction strength on co-elevation products

# Normalization bound for the interaction positive-part (the Module 4 clip).
ANOMALY_CLIP: float = 3.0  # assumed (matches anomalies.py clip)

# Risk-level cut points on the compound score. Ordered ascending by lower bound;
# a score takes the highest level whose bound it meets or exceeds.
RISK_LEVELS: tuple[tuple[str, float], ...] = (
    ("LOW", float("-inf")),  # assumed
    ("MODERATE", 1.0),       # assumed
    ("HIGH", 2.5),           # assumed
    ("SEVERE", 4.0),         # assumed
)

SIGNALS: tuple[str, ...] = tuple(WEIGHTS.keys())
ANOMALY_COLUMNS: dict[str, str] = {s: f"anomaly_{s}" for s in SIGNALS}


def classify_risk(score: float) -> str:
    """Map a compound score to a risk-level label.

    Args:
        score: The compound risk score.

    Returns:
        The label of the highest band whose lower bound ``score`` meets.
    """
    label = RISK_LEVELS[0][0]
    for name, lower in RISK_LEVELS:
        if score >= lower:
            label = name
        else:
            break
    return label


def positive_normalized(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Return the positive-part, clip-normalized anomalies a_i⁺ ∈ [0, 1].

    Args:
        anomalies: Frame with ``anomaly_<signal>`` columns in [-3, 3].

    Returns:
        DataFrame of a_i⁺ = max(a_i, 0) / ANOMALY_CLIP, one column per signal.
    """
    pos = pd.DataFrame(index=anomalies.index)
    for signal, col in ANOMALY_COLUMNS.items():
        pos[signal] = anomalies[col].clip(lower=0.0) / ANOMALY_CLIP
    return pos


def compute_compound(anomalies: pd.DataFrame) -> pd.DataFrame:
    """Compute the compound score and its full decomposition per day.

    Args:
        anomalies: Frame with ``anomaly_<signal>`` columns (Module 4 output).

    Returns:
        A DataFrame indexed by ``date`` with:
        * ``signal_<s>`` — signed linear contribution w_s · a_s (contribution of
          every signal).
        * ``int_<i>__<j>`` — interaction contribution λ · a_i⁺ · a_j⁺ (contribution
          of every interaction).
        * ``linear_total`` and ``interaction_total``.
        * ``compound_score`` and ``risk_level``.

    Raises:
        KeyError: If an expected ``anomaly_<signal>`` column is missing.
    """
    missing = [c for c in ANOMALY_COLUMNS.values() if c not in anomalies.columns]
    if missing:
        raise KeyError(f"anomalies frame missing columns: {missing}")

    out = pd.DataFrame(index=anomalies.index)
    pos = positive_normalized(anomalies)

    # Contribution of every signal (signed linear term).
    for signal, col in ANOMALY_COLUMNS.items():
        out[f"signal_{signal}"] = WEIGHTS[signal] * anomalies[col]
    linear_cols = [f"signal_{s}" for s in SIGNALS]
    out["linear_total"] = out[linear_cols].sum(axis=1)

    # Contribution of every interaction (positive-part co-elevation).
    interaction_cols: list[str] = []
    for a, b in combinations(SIGNALS, 2):
        name = f"int_{a}__{b}"
        out[name] = LAMBDA * pos[a] * pos[b]
        interaction_cols.append(name)
    out["interaction_total"] = out[interaction_cols].sum(axis=1)

    out["compound_score"] = out["linear_total"] + out["interaction_total"]
    out["risk_level"] = out["compound_score"].apply(classify_risk)

    logger.info(
        "Compound scores: min=%.2f max=%.2f mean=%.2f | HIGH/SEVERE days=%d",
        float(out["compound_score"].min()),
        float(out["compound_score"].max()),
        float(out["compound_score"].mean()),
        int(out["risk_level"].isin(["HIGH", "SEVERE"]).sum()),
    )
    return out


def interaction_matrix(anomalies_row: pd.Series) -> pd.DataFrame:
    """Build the symmetric interaction-contribution matrix for one day.

    Args:
        anomalies_row: A row of the anomalies frame (``anomaly_<signal>`` values).

    Returns:
        An N×N DataFrame indexed/columned by signal. Off-diagonal entry [i, j]
        is the interaction contribution λ · a_i⁺ · a_j⁺ for that pair; the
        diagonal is 0 (self-interaction is not part of the model). The sum of the
        upper triangle equals ``interaction_total`` for that day.
    """
    pos = {
        s: max(float(anomalies_row[col]), 0.0) / ANOMALY_CLIP
        for s, col in ANOMALY_COLUMNS.items()
    }
    mat = pd.DataFrame(0.0, index=list(SIGNALS), columns=list(SIGNALS))
    for a, b in combinations(SIGNALS, 2):
        value = LAMBDA * pos[a] * pos[b]
        mat.loc[a, b] = value
        mat.loc[b, a] = value
    return mat


def _load_anomalies() -> pd.DataFrame:
    """Build anomaly scores fresh via the Module 4 pipeline (no stale files)."""
    from anomalies import build_and_save as build_anomalies

    return build_anomalies(save=False)


def build_and_save(save: bool = True) -> pd.DataFrame:
    """Run Module 5 end to end: anomalies -> compound (optionally save).

    Args:
        save: If True, write to ``data/processed/compound.csv``.

    Returns:
        The compound-scored DataFrame.
    """
    anomalies = _load_anomalies()
    compound = compute_compound(anomalies)
    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        compound.to_csv(COMPOUND_CSV, index=True)
        logger.info("Saved compound results to %s", COMPOUND_CSV)
    return compound


if __name__ == "__main__":
    anomalies = _load_anomalies()
    df = compute_compound(anomalies)
    if True:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(COMPOUND_CSV, index=True)

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 30)

    print("=" * 88)
    print("MODULE 5 ACCEPTANCE — compound risk model")
    print("=" * 88)
    print("\nParameters (mirrored in docs/assumptions.md):")
    print(f"  weights = {WEIGHTS}   (all # assumed)")
    print(f"  lambda  = {LAMBDA}    (# assumed)")
    print(f"  interaction uses a_i+ = max(a_i,0)/{ANOMALY_CLIP}  (co-elevation, normalized)")
    print(f"  risk levels = {[(n, b) for n, b in RISK_LEVELS]}   (all # assumed)")

    print(f"\nCompound score distribution (shape {df.shape}):")
    print(df["compound_score"].describe().round(3).to_string())
    print("\nRisk-level counts:")
    print(df["risk_level"].value_counts().to_string())

    peak = df["compound_score"].idxmax()
    print(f"\nPeak-risk day: {peak.date()}  (score {df.loc[peak, 'compound_score']:.3f}, "
          f"{df.loc[peak, 'risk_level']})")
    print("\nInteraction matrix for the peak day (λ·a_i⁺·a_j⁺):")
    print(interaction_matrix(anomalies.loc[peak]).round(3).to_string())

    print("\nFull decomposition on HIGH/SEVERE days:")
    hs = df[df["risk_level"].isin(["HIGH", "SEVERE"])]
    print(hs.round(3).to_string())
