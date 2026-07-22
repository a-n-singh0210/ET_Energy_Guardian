"""geodata.py — geospatial reference data for the corridor map.

Coordinates for chokepoints, supplier origins and India's main import ports,
plus route polylines (origin → corridor → India). Coordinates are approximate
public geographic locations; routes are stylised great-circle-ish waypoints for
visualisation, not navigational paths.
"""

from __future__ import annotations

# (lat, lng)
CHOKEPOINTS: dict[str, dict[str, object]] = {
    "hormuz": {"name": "Strait of Hormuz", "lat": 26.6, "lng": 56.5},
    "bab_el_mandeb": {"name": "Bab-el-Mandeb", "lat": 12.6, "lng": 43.4},
    "suez": {"name": "Suez Canal", "lat": 30.0, "lng": 32.55},
    "cape": {"name": "Cape of Good Hope", "lat": -34.4, "lng": 18.5},
}

INDIA_PORTS: dict[str, dict[str, object]] = {
    "sikka": {"name": "Sikka / Jamnagar", "lat": 22.4, "lng": 69.8},
    "paradip": {"name": "Paradip", "lat": 20.3, "lng": 86.7},
}

# Supplier origin nodes with the corridor their barrels use to reach India.
SUPPLIERS: dict[str, dict[str, object]] = {
    "saudi": {"name": "Ras Tanura (Saudi)", "lat": 26.7, "lng": 50.0, "corridor": "hormuz"},
    "iraq": {"name": "Basra (Iraq)", "lat": 30.0, "lng": 48.2, "corridor": "hormuz"},
    "uae": {"name": "Fujairah (UAE)", "lat": 25.1, "lng": 56.35, "corridor": "hormuz"},
    "russia": {"name": "Baltic/Black Sea (Russia)", "lat": 44.6, "lng": 37.8, "corridor": "redsea"},
    "kazakhstan": {"name": "Novorossiysk (CPC)", "lat": 44.7, "lng": 37.8, "corridor": "redsea"},
    "nigeria": {"name": "Bonny (Nigeria)", "lat": 4.4, "lng": 7.2, "corridor": "atlantic_cape"},
    "angola": {"name": "Angola", "lat": -8.8, "lng": 13.2, "corridor": "atlantic_cape"},
    "brazil": {"name": "Santos (Brazil)", "lat": -24.0, "lng": -46.3, "corridor": "atlantic_cape"},
    "guyana": {"name": "Guyana", "lat": 6.8, "lng": -58.2, "corridor": "atlantic_cape"},
    "usa": {"name": "US Gulf Coast", "lat": 29.0, "lng": -94.8, "corridor": "atlantic_cape"},
    "venezuela": {"name": "Venezuela", "lat": 10.5, "lng": -64.2, "corridor": "atlantic_cape"},
    "mexico": {"name": "Mexico (Gulf)", "lat": 19.5, "lng": -92.2, "corridor": "atlantic_cape"},
}

# Waypoints per corridor from origin toward Sikka (stylised).
_WAYPOINTS: dict[str, list[list[float]]] = {
    "hormuz": [[26.6, 56.5], [24.5, 60.0], [22.4, 69.8]],
    "redsea": [[30.0, 32.55], [20.0, 38.0], [12.6, 43.4], [15.0, 55.0], [22.4, 69.8]],
    "atlantic_cape": [[-34.4, 18.5], [-10.0, 45.0], [10.0, 60.0], [22.4, 69.8]],
}


def routes() -> list[dict[str, object]]:
    """Build route polylines from each supplier to Sikka via its corridor.

    Returns:
        List of {supplier, corridor, points:[[lat,lng],...]} for the map.
    """
    out: list[dict[str, object]] = []
    for key, s in SUPPLIERS.items():
        corridor = str(s["corridor"])
        pts = [[float(s["lat"]), float(s["lng"])]] + [list(p) for p in _WAYPOINTS[corridor]]
        out.append({"supplier": key, "name": s["name"], "corridor": corridor, "points": pts})
    return out


def geo_payload() -> dict[str, object]:
    """Full geospatial payload for the API / map."""
    return {
        "chokepoints": CHOKEPOINTS,
        "india_ports": INDIA_PORTS,
        "suppliers": SUPPLIERS,
        "routes": routes(),
    }
