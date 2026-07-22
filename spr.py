"""spr.py — Strategic Petroleum Reserve drawdown optimiser.

Models whether India's SPR can bridge an import gap until rerouted procurement
cargoes arrive and ramp up. Produces a day-by-day drawdown schedule and a clear
verdict: does the reserve bridge the gap, and if not, how large is the exposure
window?

This ties the scenario (gap) to procurement (first-cargo ETA + ramp) — the
"signal → scenario → response" loop the challenge asks for.
"""

from __future__ import annotations

import india_params as P

RAMP_DAYS = 10  # assumed days for rerouted cargoes to sequence up to full volume
HORIZON_DAYS = 60


def _alt_supply(day: int, eta: int, coverage_mbd: float) -> float:
    """Alternative supply available on a given day (linear ramp after ETA).

    Args:
        day: Day index from the shock (day 0 = shock).
        eta: First-cargo arrival day.
        coverage_mbd: Steady-state volume procurement can deliver (mb/d).

    Returns:
        Alternative supply in mb/d on that day.
    """
    if day < eta:
        return 0.0
    if day >= eta + RAMP_DAYS:
        return coverage_mbd
    return coverage_mbd * (day - eta) / RAMP_DAYS


def optimise_drawdown(
    gap_mbd: float,
    first_cargo_eta_days: int | None,
    procurement_coverage_mbd: float,
    spr_mmbbl: float = P.SPR_STORED_MMBBL.value,
) -> dict[str, object]:
    """Simulate the SPR drawdown needed to bridge the gap to resupply.

    Args:
        gap_mbd: India import gap (mb/d).
        first_cargo_eta_days: Days until the first rerouted cargo arrives.
        procurement_coverage_mbd: Steady-state alternative supply (mb/d).
        spr_mmbbl: SPR volume available (million bbl).

    Returns:
        Dict with the day-by-day schedule, whether the reserve bridges, the
        exposure window (days of uncovered gap), and a verdict string.
    """
    if gap_mbd <= 1e-6:
        return {
            "bridged": True,
            "verdict": "No import gap — SPR untouched.",
            "exposure_days": 0,
            "spr_min_mmbbl": round(spr_mmbbl, 1),
            "schedule": [],
        }

    eta = first_cargo_eta_days if first_cargo_eta_days is not None else HORIZON_DAYS
    spr = spr_mmbbl
    schedule: list[dict[str, float]] = []
    exposure_days = 0
    exhausted_day: int | None = None

    for day in range(HORIZON_DAYS + 1):
        alt = _alt_supply(day, eta, procurement_coverage_mbd)
        residual = max(0.0, gap_mbd - alt)  # gap the SPR must cover today
        draw = min(residual, spr)  # mb/d drawn (can't exceed remaining)
        uncovered = residual - draw
        if uncovered > 1e-6:
            exposure_days += 1
        spr = max(0.0, spr - draw)
        if spr <= 1e-6 and exhausted_day is None and residual > 0:
            exhausted_day = day
        schedule.append(
            {
                "day": day,
                "spr_remaining_mmbbl": round(spr, 2),
                "alt_supply_mbd": round(alt, 3),
                "spr_draw_mbd": round(draw, 3),
                "uncovered_mbd": round(uncovered, 3),
            }
        )
        if alt >= gap_mbd - 1e-6 and spr >= 0:
            # Resupply fully covers the gap from here; stop early.
            break

    bridged = exposure_days == 0
    if bridged:
        verdict = (
            f"SPR bridges the gap: reserve covers {gap_mbd:.2f} mb/d until rerouted "
            f"supply ramps in by day {eta + RAMP_DAYS}."
        )
    else:
        verdict = (
            f"Exposure risk: SPR is exhausted around day {exhausted_day} but full "
            f"resupply only arrives by day {eta + RAMP_DAYS} — a {exposure_days}-day "
            f"uncovered window. Recommend demand curtailment / faster shorter-haul lifting."
        )

    return {
        "bridged": bridged,
        "verdict": verdict,
        "exposure_days": exposure_days,
        "exhausted_day": exhausted_day,
        "first_cargo_eta_days": eta,
        "full_resupply_day": eta + RAMP_DAYS,
        "spr_min_mmbbl": round(min(s["spr_remaining_mmbbl"] for s in schedule), 2),
        "schedule": schedule,
    }


if __name__ == "__main__":
    out = optimise_drawdown(1.525, 22, 1.525)
    print(out["verdict"])
    print(f"  exposure {out['exposure_days']}d | SPR min {out['spr_min_mmbbl']} mmbbl | "
          f"exhausted day {out['exhausted_day']} | full resupply day {out['full_resupply_day']}")
