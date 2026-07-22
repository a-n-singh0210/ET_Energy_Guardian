"""scenario.py — Disruption Scenario Modeller.

Simulates a geopolitical disruption (Strait of Hormuz closure, Red Sea
suspension, OPEC+ cut) and computes the cascading impact on India's crude supply:
Brent price premium, import gap, SPR bridge days, retail fuel delta, and macro
effects (GDP growth, current-account deficit, inflation).

The model is a transparent chain of documented/assumed coefficients (see
``india_params.py`` and ``docs/india_assumptions.md``). Every output is a pure
function of the inputs and those parameters — no hidden state, no live feed.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import india_params as P


@dataclass
class ScenarioInput:
    """Scenario knobs the user controls.

    Attributes:
        hormuz_closure: Fraction of Strait of Hormuz flow disrupted [0, 1].
        redsea_suspension: Fraction of Red Sea / Bab-el-Mandeb flow disrupted [0, 1].
        opec_cut_mbd: Additional OPEC+ supply cut in mb/d (>= 0).
    """

    hormuz_closure: float = 0.0
    redsea_suspension: float = 0.0
    opec_cut_mbd: float = 0.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def run_scenario(inp: ScenarioInput) -> dict[str, object]:
    """Run the disruption cascade for one scenario.

    Args:
        inp: The scenario knobs.

    Returns:
        A dict with the input echo, India supply gap, Brent price impact, SPR
        bridge, retail and macro effects, plus a short chain-of-reasoning list
        that makes the cascade auditable.
    """
    h = _clamp(inp.hormuz_closure, 0.0, 1.0)
    r = _clamp(inp.redsea_suspension, 0.0, 1.0)
    o = max(0.0, inp.opec_cut_mbd)

    imports = P.IMPORTS_MBD.value

    # 1. India-specific import volume at risk (mb/d).
    hormuz_gap = h * P.HORMUZ_SHARE_OF_IMPORTS.value * imports
    redsea_gap = r * P.REDSEA_SHARE_OF_IMPORTS.value * imports
    india_gap = hormuz_gap + redsea_gap

    # 2. Global supply loss driving the price (mb/d). Hormuz has almost no bypass
    #    (only ~2.6 mb/d pipelines); Red Sea can reroute via the Cape, so only a
    #    residual fraction of its loss persists in the price.
    hormuz_global = max(0.0, h * P.HORMUZ_GLOBAL_FLOW_MBD.value - P.HORMUZ_BYPASS_MBD.value)
    redsea_global = r * P.REDSEA_GLOBAL_FLOW_MBD.value * P.REDSEA_REROUTE_RESIDUAL.value
    global_loss = hormuz_global + redsea_global + o
    loss_fraction = global_loss / P.WORLD_SUPPLY_MBD.value

    # 3. Brent premium: inelastic demand => price multiplier = 1 / elasticity.
    premium_pct = min(
        loss_fraction * (1.0 / P.PRICE_DEMAND_ELASTICITY.value) * 100.0,
        P.PREMIUM_CAP_PCT.value,
    )
    brent = P.BRENT_BASELINE_USD.value * (1.0 + premium_pct / 100.0)
    brent_increase = brent - P.BRENT_BASELINE_USD.value

    # 4. SPR bridge: how many days the ~21.4 mmbbl reserve covers the gap.
    spr_bridge_days = (
        P.SPR_STORED_MMBBL.value / india_gap if india_gap > 1e-9 else None
    )

    # 5. Retail + macro effects (scaled by the $10-Brent sensitivities).
    per10 = brent_increase / 10.0
    fuel_delta_pct = premium_pct * P.RETAIL_PASSTHROUGH.value
    gdp_growth_hit_pp = P.GDP_GROWTH_PP_PER_10USD.value * per10
    cad_widen_pct = P.CAD_PCT_PER_10USD.value * per10
    inflation_add_bps = P.INFLATION_BPS_PER_10USD.value * per10

    # 6. Refinery run-rate at risk (unmitigated): the import gap as a share of
    #    throughput demand — the cut refiners face before SPR / rerouting.
    runrate_at_risk_pct = min(100.0, (india_gap / P.DEMAND_MBD.value) * 100.0)
    refinery_runrate_pct = max(0.0, 100.0 - runrate_at_risk_pct)

    # 7. GDP trajectory: peak hit decays as supply stabilises. Per the McKinsey
    #    reference in the brief, economies WITHOUT automated rerouting take ~47
    #    days longer to stabilise. We show both paths.
    peak = gdp_growth_hit_pp
    managed_days = 30.0  # assumed baseline stabilisation with the system
    reactive_days = managed_days + 47.0  # McKinsey: +47 days without response intelligence
    tau_m = managed_days / 30.0
    tau_r = reactive_days / 30.0
    gdp_trajectory = [
        {
            "month": m,
            "managed_pp": round(peak * math.exp(-m / tau_m), 2),
            "reactive_pp": round(peak * math.exp(-m / tau_r), 2),
        }
        for m in range(0, 7)
    ]

    severity = _severity(premium_pct, india_gap)

    reasoning = [
        f"Hormuz {h:.0%} × {P.HORMUZ_SHARE_OF_IMPORTS.value:.0%} of imports × "
        f"{imports:.2f} mb/d = {hormuz_gap:.2f} mb/d at risk",
        f"Red Sea {r:.0%} × {P.REDSEA_SHARE_OF_IMPORTS.value:.0%} × {imports:.2f} = "
        f"{redsea_gap:.2f} mb/d at risk",
        f"Global supply loss {global_loss:.2f} mb/d = {loss_fraction:.1%} of "
        f"{P.WORLD_SUPPLY_MBD.value:.0f} mb/d (Hormuz bypass {P.HORMUZ_BYPASS_MBD.value} mb/d applied)",
        f"Inelastic demand (ε={P.PRICE_DEMAND_ELASTICITY.value}) ⇒ Brent premium "
        f"{premium_pct:.0f}% ⇒ ${brent:.0f}/bbl",
        f"SPR {P.SPR_STORED_MMBBL.value} mmbbl ÷ {india_gap:.2f} mb/d gap = "
        + (f"{spr_bridge_days:.1f} days of cover" if spr_bridge_days else "no gap"),
    ]

    return {
        "input": asdict(ScenarioInput(h, r, o)),
        "india_import_gap_mbd": round(india_gap, 3),
        "hormuz_gap_mbd": round(hormuz_gap, 3),
        "redsea_gap_mbd": round(redsea_gap, 3),
        "global_supply_loss_mbd": round(global_loss, 3),
        "global_loss_fraction": round(loss_fraction, 4),
        "brent_baseline_usd": P.BRENT_BASELINE_USD.value,
        "brent_premium_pct": round(premium_pct, 1),
        "brent_price_usd": round(brent, 1),
        "spr_bridge_days": round(spr_bridge_days, 1) if spr_bridge_days else None,
        "retail_fuel_delta_pct": round(fuel_delta_pct, 1),
        "gdp_growth_hit_pp": round(gdp_growth_hit_pp, 2),
        "cad_widen_pct_gdp": round(cad_widen_pct, 2),
        "inflation_add_bps": round(inflation_add_bps, 0),
        "refinery_runrate_pct": round(refinery_runrate_pct, 1),
        "refinery_runrate_at_risk_pct": round(runrate_at_risk_pct, 1),
        "gdp_trajectory": gdp_trajectory,
        "severity": severity,
        "reasoning": reasoning,
    }


def _severity(premium_pct: float, gap_mbd: float) -> str:
    """Classify overall scenario severity from price premium and import gap.

    Args:
        premium_pct: Modelled Brent premium (%).
        gap_mbd: India import gap (mb/d).

    Returns:
        One of LOW / MODERATE / HIGH / SEVERE (assumed cut points).
    """
    score = premium_pct / 20.0 + gap_mbd  # assumed blend
    if score >= 6:
        return "SEVERE"
    if score >= 3:
        return "HIGH"
    if score >= 1:
        return "MODERATE"
    return "LOW"


# Preset scenarios for quick demo buttons.
PRESETS: dict[str, ScenarioInput] = {
    "Calm baseline": ScenarioInput(0.0, 0.0, 0.0),
    "Red Sea suspension": ScenarioInput(0.0, 0.8, 0.0),
    "Hormuz partial (30%)": ScenarioInput(0.3, 0.2, 0.0),
    "Hormuz major (60%) + OPEC+ cut": ScenarioInput(0.6, 0.3, 1.0),
    "Hormuz full closure": ScenarioInput(1.0, 0.5, 0.0),
}


if __name__ == "__main__":
    for name, inp in PRESETS.items():
        out = run_scenario(inp)
        print(f"\n=== {name} ===")
        print(
            f"  gap={out['india_import_gap_mbd']} mb/d | Brent +{out['brent_premium_pct']}% "
            f"(${out['brent_price_usd']}) | SPR bridge {out['spr_bridge_days']}d | "
            f"GDP {out['gdp_growth_hit_pp']}pp | {out['severity']}"
        )
