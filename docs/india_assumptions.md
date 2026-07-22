# India Energy-Security Model — Assumptions Register

Every parameter behind the Scenario Modeller, Procurement Orchestrator, SPR
optimiser and Historical Similarity is listed here with its value, origin
(`documented` / `assumed`) and source. This is the credibility artifact the
challenge rubric asks for: *"scenario model fidelity — assumptions must be
explicit and testable."* Change any value in `india_params.py` and every
downstream number updates transparently. Nothing here is a live feed.

## Import structure

| Parameter | Value | Origin | Source |
|---|---|---|---|
| India crude imports | 4.84 mb/d | documented | EIA India Country Analysis 2024/25 |
| Refinery throughput / demand | 5.5 mb/d | documented | EIA / PPAC |
| Import dependence | 88% | documented | Problem statement; EIA |
| Hormuz share of imports | 45% | documented | 40–45% via Hormuz (problem statement) |
| Red Sea / Suez share of imports | 15% | **assumed** | Est. Russian/Atlantic barrels via Suez |
| Import mix 2024 | Russia 36.3% · Iraq 20.5% · Saudi 13.0% · UAE 9.0% · US 3.5% · Other 17.7% | documented | Voronoi / Statista / EIA |

## Strategic Petroleum Reserve

| Parameter | Value | Origin | Source |
|---|---|---|---|
| SPR stored volume | 21.4 million bbl | documented | EIA (as of Mar 2025) |
| Full-halt cover | ~9.5 days | documented | Problem statement |
| Total cover incl. commercial | ~72 days | documented | EIA (70–74 days) |

## Global flow & price

| Parameter | Value | Origin | Source |
|---|---|---|---|
| World liquids supply | 103 mb/d | documented | EIA 2024 |
| Hormuz throughput | ~20 mb/d | documented | EIA |
| Bab-el-Mandeb throughput | ~8.8 mb/d | documented | EIA |
| Hormuz bypass pipelines | 2.6 mb/d | documented | Saudi East-West + UAE Fujairah spare |
| Red Sea reroute residual | 30% | **assumed** | Fraction of price impact persisting after Cape rerouting |
| Brent baseline | $80/bbl | **assumed** | Reference price the scenario perturbs |
| Price demand elasticity | 0.08 | **assumed** | Short-run ~0.05–0.1; price multiplier = 1/ε |
| Premium cap | 150% | **assumed** | Bounds extrapolation |

## Macro sensitivities (per +$10 Brent)

| Parameter | Value | Origin | Source |
|---|---|---|---|
| GDP growth | −0.26 pp | documented | Empirical studies (0.25–0.27 pp) |
| Current-account deficit | +0.45% of GDP | documented | 0.4–0.5% of GDP estimates |
| Inflation | +30 bps | documented | Financial-institution estimates |
| Retail fuel pass-through | 50% | **assumed** | Taxes/subsidies buffer the rest |

## Scenario cascade (scenario.py)

```
india_gap      = hormuz_closure·45%·4.84 + redsea_suspension·15%·4.84
global_loss    = max(0, hormuz·20 − 2.6) + redsea·8.8·0.30 + opec_cut
brent_premium% = min( (global_loss / 103) · (1/0.08) · 100 , 150 )
spr_bridge     = 21.4 mmbbl ÷ india_gap
gdp / cad / cpi = per-$10 sensitivities × (Brent increase / 10)
```
> Validation check: a **full Hormuz closure** yields an ~8–9 day SPR bridge,
> consistent with the documented ~9.5-day cover — the model reproduces the known
> figure from independent parameters.

## Procurement (procurement.py)

Alternative crude sources carry reference attributes (grade, API, sulfur,
approximate voyage days to India's west coast, spot premium/discount over Brent,
spare liftable volume, refinery-grade fit). Values are **assumed reference
levels** for prototype ranking, not live spot quotes. Sources on a disrupted
corridor are penalised so the orchestrator prefers resilient Atlantic/Cape
barrels. Ranking minimises landed cost adjusted for transit time and grade fit.

## SPR optimiser (spr.py)

Cargo ramp after first-cargo ETA = 10 days (**assumed**). The optimiser reports
whether the reserve bridges the gap until resupply, and any exposure window.

## Historical Similarity (similarity.py)

Cosine similarity on standardised features `[price shock %, supply loss mb/d,
Hormuz flag, Red Sea flag]`. Historical magnitudes are documented public figures
(Abqaiq 2019 ~5.7 mb/d / +15%; Gulf War 1990 ~doubling; Russia 2022 +30%; Ever
Given 2021 ~+4%; Red Sea 2023–24; US-Iran 2025 +8%). Feature scales are assumed.

## Detection backbone

The live risk-detection engine (compound model on real 2023–24 Red Sea data,
Brent + freight + corridor events) validates **signal lead time and accuracy** —
see the main `docs/assumptions.md` and the Compound-vs-Baseline analysis.
