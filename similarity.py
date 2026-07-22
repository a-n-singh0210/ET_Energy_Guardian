"""similarity.py — Historical Similarity.

When a scenario is elevated, surface the most similar historical energy-supply
shocks by comparing structured feature vectors (price shock, supply loss,
chokepoint involvement). Similarity is cosine on standardised features — a
transparent nearest-neighbour lookup, not a black box.

Historical magnitudes are documented public figures (cited in the notes); the
feature encoding is an explicit modelling choice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HistEvent:
    """A historical supply shock with its structured features.

    Attributes:
        name: Event label.
        year: Year.
        price_shock_pct: Peak Brent move attributed to the event (%).
        supply_loss_mbd: Approx. peak supply disrupted (mb/d).
        hormuz: 1 if it involved the Strait of Hormuz / Persian Gulf.
        redsea: 1 if it involved the Red Sea / Bab-el-Mandeb / Suez.
        note: Source / context.
    """

    name: str
    year: int
    price_shock_pct: float
    supply_loss_mbd: float
    hormuz: int
    redsea: int
    note: str


# Documented historical shocks (magnitudes from public reporting).
EVENTS: list[HistEvent] = [
    HistEvent("Red Sea / Houthi attacks", 2023, 8, 0.0, 0, 1,
              "Container freight +130%; modest crude move; Cape rerouting (Reuters/ITF-OECD)"),
    HistEvent("Ever Given Suez blockage", 2021, 4, 0.0, 0, 1,
              "6-day Suez blockage; brief ~4% Brent move (widely reported)"),
    HistEvent("Abqaiq attack", 2019, 15, 5.7, 1, 0,
              "Drone strike cut ~5.7 mb/d Saudi output; Brent +~15% single day (EIA/Reuters)"),
    HistEvent("Hormuz tanker attacks", 2019, 4, 0.0, 1, 0,
              "May-June 2019 Gulf of Oman tanker attacks; small Brent move"),
    HistEvent("Russia invasion of Ukraine", 2022, 30, 3.0, 0, 0,
              "Brent to ~$130 (+30%); ~3 mb/d Russian flows re-routed/sanctioned"),
    HistEvent("Gulf War (Iraq/Kuwait)", 1990, 90, 4.3, 1, 0,
              "Brent roughly doubled; ~4.3 mb/d Iraqi+Kuwaiti supply lost"),
    HistEvent("US-Iran standoff", 2025, 8, 0.0, 1, 0,
              "Brent +8% single session; spot-market premiums (problem statement)"),
]

# Reference scales for standardising features (assumed, order-of-magnitude).
_SCALE = {"price": 30.0, "supply": 5.0, "hormuz": 1.0, "redsea": 1.0}


def _vec(price: float, supply: float, hormuz: float, redsea: float) -> list[float]:
    return [
        price / _SCALE["price"],
        supply / _SCALE["supply"],
        hormuz / _SCALE["hormuz"],
        redsea / _SCALE["redsea"],
    ]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return dot / (na * nb)


def rank_similar(
    price_shock_pct: float,
    supply_loss_mbd: float,
    hormuz: bool,
    redsea: bool,
    top_k: int = 3,
) -> list[dict[str, object]]:
    """Rank historical events by similarity to the current scenario.

    Args:
        price_shock_pct: Scenario Brent premium (%).
        supply_loss_mbd: Scenario global supply loss (mb/d).
        hormuz: Whether the scenario involves Hormuz.
        redsea: Whether the scenario involves the Red Sea.
        top_k: Number of matches to return.

    Returns:
        List of {name, year, similarity, note, ...} sorted by similarity desc.
    """
    cur = _vec(price_shock_pct, supply_loss_mbd, 1.0 if hormuz else 0.0, 1.0 if redsea else 0.0)
    scored = []
    for e in EVENTS:
        sim = _cosine(cur, _vec(e.price_shock_pct, e.supply_loss_mbd, e.hormuz, e.redsea))
        scored.append(
            {
                "name": e.name,
                "year": e.year,
                "similarity": round(sim, 2),
                "price_shock_pct": e.price_shock_pct,
                "supply_loss_mbd": e.supply_loss_mbd,
                "note": e.note,
            }
        )
    scored.sort(key=lambda d: d["similarity"], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    for m in rank_similar(135.8, 9.4, hormuz=True, redsea=True):
        print(f"  {m['similarity']:.2f}  {m['name']} ({m['year']}) — {m['note'][:60]}")
