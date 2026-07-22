# EnergyGuardian AI — Specification (v2)

> This document records the specification for the detection engine and its
> build order.

## Fixed architecture (do not change)

**Language:** Python 3.11

**Libraries:** pandas, numpy, matplotlib, streamlit, scikit-learn,
python-dotenv, yfinance.

No FastAPI. No NextJS. No LangChain. No agents. No vector databases. No RAG. No
forecasting. No digital twin. No graph models. No additional dependencies
unless explicitly approved.

## Project thesis

EnergyGuardian AI identifies compound disruptions by modelling interactions
between weak public signals. Traditional monitoring treats every signal
independently. EnergyGuardian evaluates how multiple weak anomalies interact to
produce elevated systemic risk. The compound interaction layer is the
innovation.

## Data sources

Use only public data.

1. **Brent prices** — yfinance, ticker `BZ=F`, context only.
2. **Manual Red Sea event log** — CSV maintained in `/data`, documented public
   sources, every event cited in `docs/sources.md`.
3. **Freight / shipping disruption proxy** — documented public values, stored
   locally as CSV.

No fabricated observations. If data is unavailable: state the limitation; do not
invent values.

## Feature engineering

Produce reproducible features. Examples: rolling return, rolling volatility,
rolling z-score, event frequency, event severity, carrier suspension indicator,
insurance premium indicator, transit reduction indicator. Document every
feature.

## Anomaly engine

Compute anomaly scores independently. Rolling window = 14 days. Use robust
z-scores. Clip to [-3, 3]. Normalize if required. Document every transformation.

## Compound risk model

Implement exactly:

```
Risk(t) = Σ wi·ai(t)  +  λ Σ ai(t)·aj(t)
```

Weights and λ must appear once at the top of `compound.py`. Every parameter must
be tagged `# assumed` or `# estimated`. Mirror every parameter into
`docs/assumptions.md`.

The compound layer must also return:
- contribution of every signal
- contribution of every interaction
- final score

No hidden calculations.

## Baseline

Implement a fair baseline: an independent threshold engine that alerts if any
signal exceeds its threshold. The baseline exists only for comparison. Do not
intentionally weaken it.

## Validation

Compute: lead time, false positives, false negatives, baseline vs compound
comparison, threshold sensitivity. Generate figures automatically. Never
fabricate metrics.

## LLM

Google Gemini API (AI Studio free tier) only. The LLM may only extract
structured fields from news and output JSON. The LLM must never invent facts,
metrics, historical claims, or predictions. Explanations are fully deterministic
templates with no LLM in the loop.

## Explanations

Generated explanations must originate from model outputs, with the trace:

```
Raw signals → Anomaly scores → Interaction contributions → Final score → Human-readable explanation
```

Every sentence must be traceable.

## Streamlit

The dashboard contains NO business logic. It only visualizes backend outputs. No
calculations inside UI components.

## Module order

| # | Module | Acceptance |
|---|--------|-----------|
| 1 | `data/red_sea_events.csv`, `data/freight_proxy.csv`, optional `data/brent.csv` | print heads, shapes, source documentation |
| 2 | `ingestion.py` (load, validate, merge) | print merged dataframe |
| 3 | `features.py` (engineered features) | display engineered dataframe |
| 4 | `anomalies.py` (anomaly scores) | display anomaly dataframe |
| 5 | `compound.py` (score, interaction matrix, per-feature contributions, risk level) | print outputs |
| 6 | `baseline.py` (independent threshold engine) | print baseline alerts |
| 7 | `validate.py` (lead time, comparison metrics, plots, threshold sensitivity) | print metrics, save plots |
| 8 | `explain.py` (traceable deterministic explanations) | print explanations |
| 9 | dashboard (Timeline, Signals, Compound vs Baseline, Explanation, Assumptions, Replay) | dashboard runs without errors |

## Rules

If blocked > 30 minutes: simplify, state the limitation, continue. Do not
rabbit-hole. Do not silently change architecture. Do not fabricate data,
evaluation, or AI. Do not optimize prematurely. Readable code over clever code.
If you disagree with an architectural decision: state the concern in one
sentence, wait for approval, never implement the change yourself.
