# Assumptions Register

Every model parameter, with its value and origin (`assumed` / `estimated`),
mirrored from `compound.py` (the single place they are defined). This is the
credibility artifact required by `docs/spec.md`.

## Compound model — `Risk(t) = Σ wᵢ·aᵢ(t) + λ·Σ aᵢ⁺·aⱼ⁺`

| Parameter | Value | Origin | Notes |
|---|---|---|---|
| `w_brent` | 1.0 | assumed | Linear weight on the Brent context anomaly. Equal weighting; no evidential basis to prefer one signal. |
| `w_freight` | 1.0 | assumed | Linear weight on the freight (WCI) anomaly. |
| `w_events` | 1.0 | assumed | Linear weight on the corridor-event anomaly. |
| `λ` (lambda) | 1.5 | assumed | Interaction strength on co-elevation products. |
| Anomaly clip | 3.0 | assumed | From `anomalies.py`; also the normalization bound for the interaction positive-part. |

## Interaction modeling choice (approved)

The **linear term** uses the *signed* anomaly scores `aᵢ ∈ [-3, 3]`, so an
unusually low signal reduces its own linear contribution.

The **interaction term** uses the *positive part, normalized by the clip bound*:

```
aᵢ⁺ = max(aᵢ, 0) / 3   ∈ [0, 1]
interaction = λ · Σ_{i<j} aᵢ⁺ · aⱼ⁺
```

**Rationale:** the interaction is intended to capture the **co-elevation** of
risk indicators, not co-depression. Using signed scores directly would let two
unusually *calm* signals multiply into positive risk, which is not the intent.
Normalizing by the clip bound keeps `λ` interpretable on a `[0,1]×[0,1]` product.

## Risk-level cut points (on the compound score)

| Level | Lower bound | Origin |
|---|---|---|
| LOW | −∞ | assumed |
| MODERATE | 1.0 | assumed |
| HIGH | 2.5 | assumed |
| SEVERE | 4.0 | assumed |

> Observed on the current dataset (2023-10-01 → 2024-03-31): LOW 156 days,
> MODERATE 22, HIGH 5, SEVERE 0. No day reached SEVERE — reported honestly, not
> tuned to force one.

## Anomaly engine (from `anomalies.py`)

| Parameter | Value | Origin | Notes |
|---|---|---|---|
| Rolling window | 14 days | fixed by spec | Brent scored over 14 trading observations; freight/events over 14 calendar days. |
| Robust z scale | 1.4826·MAD | standard | Consistent estimator of σ for normal data. |
| Clip | [-3, 3] | fixed by spec | Zero-dispersion (MAD=0) windows → 0; warmup → 0. |

## Feature engineering (from `features.py`)

| Parameter | Value | Origin | Notes |
|---|---|---|---|
| Rolling window | 14 days | assumed | Matches the anomaly window. |
| `freight_wci_ffill` | forward-fill | assumed | Sparse 5-point WCI carried forward between documented prints (see `docs/sources.md`). |

## Validation (from `validate.py`)

| Parameter | Value | Origin | Notes |
|---|---|---|---|
| Ground-truth events | severity ≥ 4 | assumed | 10 documented "disruption events" to detect. |
| Systemic onset | 2023-12-15 | documented | Carrier suspensions begin; used for headline lead time. |
| Detection tolerance | ±3 days | assumed | An alert within ±3d of an event counts as a detection. |
| Lead lookback | 30 days | assumed | How far before onset an alert may lead. |
| Compound alert threshold | 2.5 | assumed | = HIGH risk bound. |

> Result at the operating point (compound ≥ 2.5, baseline z ≥ 2.0): compound
> detects 3 of 10 events with 2 false-positive days; baseline detects 1 with 3.
> Both first alert 7 days before the systemic onset (both catch the 8 Dec Brent
> spike). Both miss most *isolated* single incidents (high FN): a lone severe
> event does not move the 14-day robust-z enough to alert — the models surface
> clustered / systemic disruption, not every individual strike. Reported as-is.

## Data caveats

- **Event severity (1–5)** is an assigned ordinal, not a measured quantity.
- **Freight proxy is sparse** (5 documented WCI prints); its anomaly is
  correspondingly sparse. Stated in `docs/sources.md`, not fabricated.
- Spec-suggested `insurance_premium_indicator` and `transit_reduction_indicator`
  are omitted — no public data sourced.
