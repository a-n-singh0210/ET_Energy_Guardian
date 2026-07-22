# Sources & Citations

Every observation used by EnergyGuardian AI comes from a documented public
source. This file is the citation register required by `docs/spec.md`. No values
are fabricated; where data is sparse or approximate it is stated explicitly.

## Data files covered

- `data/red_sea_events.csv` — manual Red Sea corridor event log.
- `data/freight_proxy.csv` — freight / shipping-disruption proxy (Drewry World
  Container Index composite, USD per 40ft container).
- `data/brent.csv` — Brent crude context prices (`BZ=F`), pulled with `yfinance`.

---

## Red Sea event log — citations

Event dates and descriptions are documented public incidents from the 2023–24
Red Sea shipping crisis, cross-checked against the authoritative timelines below.

| id | Source | Covers |
|----|--------|--------|
| S-EV1 | Wikipedia, "Red Sea crisis" — https://en.wikipedia.org/wiki/Red_Sea_crisis and "Houthi attacks on commercial vessels" — https://en.wikipedia.org/wiki/Houthi_attacks_on_commercial_vessels | Galaxy Leader seizure (19 Nov 2023), Bab-el-Mandeb vessel attacks (early Dec 2023), carrier diversions (mid-Dec 2023), Operation Prosperity Guardian (18 Dec 2023), Gibraltar Eagle, Marlin Luanda, Rubymar, True Confidence incidents |
| S-EV2 | Reuters / gCaptain reporting on the Maersk Gibraltar near-miss and Maersk's Red Sea suspension — gCaptain "Red Sea Crisis: A Timeline" https://gcaptain.com/red-sea-crisis-a-timeline-of-maritime-chaos-over-the-past-year/ | Missile near-miss on Maersk Gibraltar and Maersk transit suspension (14–15 Dec 2023) |
| S-EV3 | Wilson Center, "Timeline: Houthi Attacks" — https://www.wilsoncenter.org/article/timeline-houthi-attacks | US–UK airstrikes on Yemen (11–12 Jan 2024) |

**Severity** (1–5) is an **assigned ordinal** reflecting shipping-disruption
impact (1 = minor incident, 5 = systemic/market-moving). It is an analyst
judgement, not a measured quantity, and is tagged as an assumption in
`docs/assumptions.md` when it feeds the model.

---

## Freight proxy — citations

Drewry World Container Index (WCI) composite freight rate, USD per 40ft
container. Values are documented weekly assessments quoted in public reporting.

| id | Date | Value (USD/40ft) | Source |
|----|------|------------------|--------|
| S-FR1 | 2023-10 (reference) | 1,342 | Industry reporting citing Drewry WCI, "as of October 2023 … 6% below the 2019 average of $1,420, lowest in 3 years" (HKEX-listed industry overview) https://www1.hkexnews.hk/listedco/listconews/sehk/2024/1101/11422536/sehk24101401391.pdf |
| S-FR2 | 2023-12-14 | 1,521 | Hellenic Shipping News, "Drewry: World Container Index Up By 4%" https://www.hellenicshippingnews.com/drewry-world-container-index-up-by-4/ |
| S-FR3 | 2023-12-21 | 1,661 | AJOT, "Drewry World Container Index — 21 Dec" https://www.ajot.com/news/drewry-world-container-index-21-dec |
| S-FR4 | 2024-01-18 | 3,777 | AJOT / Drewry, "World Container Index — 18 Jan" (composite $3,777 per 40ft) |
| S-FR5 | 2024-01-25 | 3,964 | ITF-OECD, "The Red Sea Crisis: Impacts on global shipping" — peak of USD 3,964 per 40ft by end of January 2024 https://www.itf-oecd.org/sites/default/files/repositories/red-sea-crisis-impacts-global-shipping.pdf |

### Freight proxy limitations (stated, not fabricated)

- The proxy is **sparse**: only the 5 documented values above were verified from
  public sources within scope. The Drewry WCI is published weekly, but the full
  intermediate weekly series was not obtainable from free public sources without
  inventing values, which the spec forbids.
- The 2023-10-01 baseline (S-FR1) is a **monthly reference** for October 2023,
  not a specific weekly print; it is dated to the 1st for alignment.
- S-FR5 is documented by ITF-OECD as an **end-January 2024 peak**; the exact
  weekly print date is approximate (dated to 25 Jan).
- How to align/interpolate this sparse series with the daily event and price
  data is a **modelling decision deferred to later modules**; raw observations
  are never fabricated to fill gaps.

---

## Brent crude — source

- Ticker `BZ=F` (Brent front-month futures), Yahoo Finance via the `yfinance`
  library. Window 2023-10-01 → 2024-03-31. Context signal only, per spec.
