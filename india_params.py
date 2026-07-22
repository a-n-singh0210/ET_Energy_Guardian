"""india_params.py — India energy-security parameters (single source of truth).

Every parameter used by the scenario / procurement / SPR engines lives here with
an explicit `SOURCE` note, so the "assumptions must be explicit and testable"
requirement is met literally. Values are either documented public figures
(cited) or clearly-labelled modelling assumptions.

Nothing here is a live feed — these are reference parameters a scenario is run
against. Change a value and every downstream number updates transparently.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    """A single parameter: its value, unit, origin and source note."""

    value: float
    unit: str
    origin: str  # "documented" | "assumed"
    source: str


# --------------------------------------------------------------------------- #
# India crude import structure
# --------------------------------------------------------------------------- #
IMPORTS_MBD = Param(4.84, "mb/d", "documented", "EIA India Country Analysis 2024/25 — India crude imports ~4.84 mb/d")
DEMAND_MBD = Param(5.5, "mb/d", "documented", "India refinery throughput / consumption ~5.4-5.5 mb/d (EIA, PPAC)")
IMPORT_DEPENDENCE = Param(0.88, "fraction", "documented", "India imports ~88% of crude (problem statement, EIA)")

HORMUZ_SHARE_OF_IMPORTS = Param(0.45, "fraction", "documented", "40-45% of India crude transits the Strait of Hormuz (problem statement)")
REDSEA_SHARE_OF_IMPORTS = Param(0.15, "fraction", "assumed", "Est. share of India crude via Suez/Red Sea (Russian/Atlantic barrels); modelling assumption")

# 2024 import source mix (share of imports). Source: Voronoi/Statista/EIA 2024.
IMPORT_MIX = {
    "Russia": 0.363,
    "Iraq": 0.205,
    "Saudi Arabia": 0.130,
    "UAE": 0.090,
    "United States": 0.035,
    "Other": 0.177,
}
IMPORT_MIX_SOURCE = "India crude import mix 2024: Russia 36.3%, Iraq 20.5%, Saudi 13.0%, UAE 9.0%, US 3.5% (Voronoi/Statista/EIA)"

# --------------------------------------------------------------------------- #
# Strategic Petroleum Reserve
# --------------------------------------------------------------------------- #
SPR_STORED_MMBBL = Param(21.4, "million bbl", "documented", "India SPR held ~21.4 million bbl as of Mar 2025 (EIA)")
SPR_FULL_HALT_COVER_DAYS = Param(9.5, "days", "documented", "~9.5 days national consumption cover at full import halt (problem statement)")
TOTAL_COVER_DAYS = Param(72.0, "days", "documented", "~70-74 days incl. commercial + refinery stocks (EIA)")

# --------------------------------------------------------------------------- #
# Global oil-flow context (for price impact)
# --------------------------------------------------------------------------- #
WORLD_SUPPLY_MBD = Param(103.0, "mb/d", "documented", "Global liquids supply ~103 mb/d (EIA 2024)")
HORMUZ_GLOBAL_FLOW_MBD = Param(20.0, "mb/d", "documented", "~20 mb/d oil+products transit Hormuz (EIA)")
REDSEA_GLOBAL_FLOW_MBD = Param(8.8, "mb/d", "documented", "~8-9 mb/d oil+products transit Bab-el-Mandeb (EIA)")
HORMUZ_BYPASS_MBD = Param(2.6, "mb/d", "documented", "Effective spare via Saudi East-West + UAE Fujairah pipelines (~2.6 mb/d; ~3.5 nameplate)")
REDSEA_REROUTE_RESIDUAL = Param(0.30, "fraction", "assumed", "Fraction of Red Sea price impact that persists after Cape-of-Good-Hope rerouting")

# --------------------------------------------------------------------------- #
# Price / macro sensitivities
# --------------------------------------------------------------------------- #
BRENT_BASELINE_USD = Param(80.0, "USD/bbl", "assumed", "Reference Brent price the scenario perturbs from")
PRICE_DEMAND_ELASTICITY = Param(0.08, "abs", "assumed", "Short-run price elasticity of oil demand ~0.05-0.1; price multiplier = 1/elasticity")
PREMIUM_CAP_PCT = Param(150.0, "percent", "assumed", "Cap on modelled Brent premium to avoid unbounded extrapolation")

GDP_GROWTH_PP_PER_10USD = Param(0.26, "pp per $10", "documented", "Sustained +$10 Brent cuts India GDP growth ~0.25-0.27 pp (empirical studies)")
CAD_PCT_PER_10USD = Param(0.45, "% of GDP per $10", "documented", "+$10 Brent widens India current-account deficit ~0.4-0.5% of GDP")
INFLATION_BPS_PER_10USD = Param(30.0, "bps per $10", "documented", "+$10 Brent adds ~30 bps to inflation (financial-institution estimates)")
RETAIL_PASSTHROUGH = Param(0.50, "fraction", "assumed", "Share of crude price change passed to retail fuel (taxes/subsidies buffer the rest)")

# 2025 anchor for calibration/context.
ANCHOR_2025 = "2025 US-Iran standoff: Brent +8% in a single session (problem statement)"


def all_params() -> dict[str, dict[str, object]]:
    """Return every Param as a serializable dict (for the API / assumptions UI).

    Returns:
        Mapping of parameter name -> {value, unit, origin, source}.
    """
    out: dict[str, dict[str, object]] = {}
    for name, val in globals().items():
        if isinstance(val, Param):
            out[name] = {
                "value": val.value,
                "unit": val.unit,
                "origin": val.origin,
                "source": val.source,
            }
    return out
