"""ais.py — AIS-derived chokepoint vessel traffic (IMF PortWatch).

Pulls real, AIS-derived vessel-transit counts for the maritime chokepoints that
matter to India's crude supply, from the IMF PortWatch open database (which is
built from satellite AIS vessel tracking). This is genuine geospatial vessel
intelligence — not simulated positions.

Source: IMF PortWatch (portwatch.imf.org), chokepoints database (AIS-derived).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

PORTWATCH_URL = (
    "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
    "PortWatch_chokepoints_database/FeatureServer/0/query"
)

# PortWatch chokepoint name -> our corridor key (which corridor it belongs to).
CHOKEPOINT_CORRIDOR = {
    "Strait of Hormuz": "hormuz",
    "Bab el-Mandeb Strait": "redsea",
    "Suez Canal": "redsea",
    "Cape of Good Hope": "atlantic_cape",
    "Malacca Strait": "other",
}


def fetch_chokepoints() -> list[dict]:
    """Fetch AIS-derived vessel counts for the supply-relevant chokepoints.

    Returns:
        List of dicts: ``{name, corridor, lat, lon, vessel_total, vessel_tanker,
        tanker_share}`` for the chokepoints in ``CHOKEPOINT_CORRIDOR``. Empty on
        network failure.
    """
    params = {
        "where": "1=1",
        "outFields": "portname,lat,lon,vessel_count_total,vessel_count_tanker",
        "f": "json",
    }
    url = f"{PORTWATCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20
        ).read()
    except Exception:  # noqa: BLE001 - degrade gracefully offline
        return []

    data = json.loads(raw)
    out: list[dict] = []
    for feat in data.get("features", []):
        a = feat["attributes"]
        name = a.get("portname")
        if name not in CHOKEPOINT_CORRIDOR:
            continue
        total = int(a.get("vessel_count_total") or 0)
        tanker = int(a.get("vessel_count_tanker") or 0)
        out.append(
            {
                "name": name,
                "corridor": CHOKEPOINT_CORRIDOR[name],
                "lat": a.get("lat"),
                "lon": a.get("lon"),
                "vessel_total": total,
                "vessel_tanker": tanker,
                "tanker_share": round(tanker / total, 3) if total else 0.0,
            }
        )
    # Order by tanker traffic (most oil-critical first).
    out.sort(key=lambda c: c["vessel_tanker"], reverse=True)
    return out


if __name__ == "__main__":
    for c in fetch_chokepoints():
        print(f"{c['name'][:22]:24} corridor={c['corridor']:14} "
              f"tankers={c['vessel_tanker']:>6} ({c['tanker_share']:.0%} of {c['vessel_total']})")
