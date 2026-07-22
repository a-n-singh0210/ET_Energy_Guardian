"""procurement.py — Adaptive Procurement Orchestrator.

Given a scenario's India import gap and the disrupted corridors, ranks
alternative crude sources / logistics routes and produces an *executable*
procurement recommendation: which grades to lift, how much, at what landed cost,
via which corridor, and when the first cargo can arrive.

Crude attributes are reference values / modelling assumptions (grade, API,
approximate voyage time to India's west coast, spot premium over Brent, spare
liftable volume, refinery-grade fit). They are explicit and editable — see
``docs/india_assumptions.md``. This is decision support, not a live trading feed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrudeSource:
    """An alternative crude source and its logistics profile.

    Attributes:
        name: Crude grade / stream name.
        origin: Producing country / basin.
        corridor: Chokepoint dependency — "hormuz", "redsea" or "atlantic_cape"
            (Atlantic-basin barrels routed via the Cape avoid both chokepoints).
        api: API gravity (degrees).
        sulfur_pct: Sulfur content (%).
        transit_days: Approx. voyage time to India's west coast (Sikka/Jamnagar).
        premium_usd: Spot landed premium (+) or discount (-) over Brent, USD/bbl.
        spare_mbd: Incremental volume India could realistically lift, mb/d.
        compat: Refinery-grade compatibility with Indian refineries [0, 1].
    """

    name: str
    origin: str
    corridor: str
    api: float
    sulfur_pct: float
    transit_days: int
    premium_usd: float
    spare_mbd: float
    compat: float


# Reference set of alternative sources (assumptions; see assumptions register).
SOURCES: list[CrudeSource] = [
    CrudeSource("Bonny Light", "Nigeria", "atlantic_cape", 34, 0.15, 22, 2.0, 0.40, 0.90),
    CrudeSource("Girassol", "Angola", "atlantic_cape", 30, 0.30, 24, 1.5, 0.30, 0.85),
    CrudeSource("Tupi / Lula", "Brazil", "atlantic_cape", 29, 0.35, 40, 1.0, 0.40, 0.85),
    CrudeSource("Liza", "Guyana", "atlantic_cape", 32, 0.10, 38, 2.5, 0.30, 0.88),
    CrudeSource("WTI Midland", "United States", "atlantic_cape", 40, 0.20, 38, 3.0, 0.50, 0.85),
    CrudeSource("Maya", "Mexico", "atlantic_cape", 22, 2.60, 42, -3.0, 0.20, 0.78),
    CrudeSource("Merey", "Venezuela", "atlantic_cape", 16, 2.80, 40, -8.0, 0.30, 0.72),
    CrudeSource("Urals", "Russia", "redsea", 31, 1.30, 35, -6.0, 0.60, 0.90),
    CrudeSource("CPC Blend", "Kazakhstan", "redsea", 45, 0.55, 30, 1.5, 0.20, 0.88),
    CrudeSource("Basra Medium", "Iraq", "hormuz", 29, 2.80, 6, 0.5, 0.30, 0.90),
    CrudeSource("Arab Light", "Saudi Arabia", "hormuz", 33, 1.90, 5, 1.0, 0.35, 0.92),
]


def _effective_cost(src: CrudeSource, brent_usd: float, disrupted: set[str]) -> float:
    """Score a source by landed cost, adjusted for transit and grade fit.

    Lower is better. Sources on a disrupted corridor get a large penalty so they
    fall to the bottom without being hard-excluded (still shown, ranked last).

    Args:
        src: The crude source.
        brent_usd: Current Brent price (USD/bbl).
        disrupted: Set of disrupted corridor keys.

    Returns:
        A comparable cost score (USD/bbl-equivalent).
    """
    landed = brent_usd + src.premium_usd
    transit_penalty = src.transit_days * 0.15  # ~$/bbl carrying/time cost (assumed)
    compat_bonus = (src.compat - 1.0) * 10.0  # better fit lowers effective cost
    corridor_penalty = 1000.0 if src.corridor in disrupted else 0.0
    return landed + transit_penalty + compat_bonus + corridor_penalty


def orchestrate(
    gap_mbd: float,
    brent_usd: float,
    disrupted_corridors: set[str],
) -> dict[str, object]:
    """Rank sources and allocate volume to close the import gap.

    Args:
        gap_mbd: India import gap to backfill (mb/d).
        brent_usd: Current Brent price (USD/bbl), from the scenario.
        disrupted_corridors: Corridors that are compromised (e.g. {"hormuz"}).

    Returns:
        A dict with the ranked recommendation list, blended landed cost,
        first-cargo ETA (days), coverage achieved, and residual gap.
    """
    ranked = sorted(SOURCES, key=lambda s: _effective_cost(s, brent_usd, disrupted_corridors))

    remaining = max(0.0, gap_mbd)
    recs: list[dict[str, object]] = []
    total_cost = 0.0
    total_volume = 0.0
    first_eta: int | None = None

    for src in ranked:
        if remaining <= 1e-6:
            usable = 0.0
        else:
            usable = min(src.spare_mbd, remaining)
        on_disrupted = src.corridor in disrupted_corridors
        landed = brent_usd + src.premium_usd
        if usable > 0 and not on_disrupted:
            remaining -= usable
            total_cost += landed * usable
            total_volume += usable
            if first_eta is None or src.transit_days < first_eta:
                first_eta = src.transit_days
        recs.append(
            {
                "name": src.name,
                "origin": src.origin,
                "corridor": src.corridor,
                "grade": _grade_label(src),
                "api": src.api,
                "sulfur_pct": src.sulfur_pct,
                "transit_days": src.transit_days,
                "premium_usd": src.premium_usd,
                "landed_usd": round(landed, 1),
                "spare_mbd": src.spare_mbd,
                "allocated_mbd": round(usable if not on_disrupted else 0.0, 3),
                "compat": src.compat,
                "status": "disrupted" if on_disrupted else ("selected" if usable > 0 else "standby"),
            }
        )

    coverage = total_volume
    blended = (total_cost / total_volume) if total_volume > 0 else None
    return {
        "gap_mbd": round(gap_mbd, 3),
        "coverage_mbd": round(coverage, 3),
        "coverage_pct": round(100.0 * coverage / gap_mbd, 1) if gap_mbd > 1e-6 else 100.0,
        "residual_gap_mbd": round(max(0.0, remaining), 3),
        "blended_landed_usd": round(blended, 1) if blended else None,
        "first_cargo_eta_days": first_eta,
        "recommendations": recs,
    }


def _grade_label(src: CrudeSource) -> str:
    """Human grade label from API gravity and sulfur."""
    weight = "light" if src.api >= 32 else "medium" if src.api >= 25 else "heavy"
    sweetness = "sweet" if src.sulfur_pct < 0.5 else "sour"
    return f"{weight} {sweetness}"


if __name__ == "__main__":
    # Demo: a Hormuz-major scenario leaves ~1.5 mb/d gap, Brent ~$189.
    out = orchestrate(1.525, 188.7, {"hormuz"})
    print(f"Gap {out['gap_mbd']} mb/d | coverage {out['coverage_pct']}% | "
          f"blended ${out['blended_landed_usd']} | first cargo {out['first_cargo_eta_days']}d\n")
    for r in out["recommendations"]:
        if r["status"] == "selected":
            print(f"  ✓ {r['name']:14} {r['origin']:14} {r['allocated_mbd']} mb/d "
                  f"@ ${r['landed_usd']} ({r['grade']}, {r['transit_days']}d, {r['corridor']})")
