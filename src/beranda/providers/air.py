"""Air quality, UV index and pollen, from Open-Meteo's free air-quality API (no key).

The numbers come from the Copernicus (CAMS) forecast. Pollen only exists for Europe and only
during the pollen season; outside of it the pollen list is simply empty. `parse` is a pure
function so it can be tested without a network.
"""

from __future__ import annotations

import httpx

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
USER_AGENT = "Beranda/0.14 (+https://github.com/regis57/Beranda)"
POLLENS = ("alder", "birch", "grass", "mugwort", "olive", "ragweed")

# Upper edge of each band: good / fair / moderate / poor / very poor / extremely poor.
EU_BANDS = (20, 40, 60, 80, 100)
US_BANDS = (50, 100, 150, 200, 300)
# UV index: low / moderate / high / very high / extreme (the WHO scale).
UV_BANDS = (3, 6, 8, 11)
# Pollen grains per cubic metre, a coarse common scale: none / low / moderate / high / very high.
# Real thresholds differ from one plant to another; this is only a rough guide.
POLLEN_BANDS = (1, 20, 100, 500)


def _level(value: float, bands: tuple[int, ...]) -> int:
    return sum(1 for edge in bands if value >= edge)


def build_params(latitude: float, longitude: float) -> dict:
    current = ["european_aqi", "us_aqi", "pm10", "pm2_5", "uv_index", *(f"{p}_pollen" for p in POLLENS)]
    return {"latitude": latitude, "longitude": longitude, "timezone": "auto", "current": ",".join(current)}


def parse(payload: dict, us_scale: bool = False) -> dict:
    cur = payload.get("current") or {}
    aqi = cur.get("us_aqi" if us_scale else "european_aqi")
    uv = cur.get("uv_index")
    pollen = []
    for kind in POLLENS:
        value = cur.get(f"{kind}_pollen")
        if value is not None and value >= POLLEN_BANDS[0]:
            pollen.append({"kind": kind, "value": round(value), "level": _level(value, POLLEN_BANDS)})
    pollen.sort(key=lambda p: -p["value"])
    return {
        "aqi": None if aqi is None else round(aqi),
        "aqi_level": None if aqi is None else _level(aqi, US_BANDS if us_scale else EU_BANDS),
        "aqi_scale": "us" if us_scale else "eu",
        "uv": None if uv is None else round(uv, 1),
        "uv_level": None if uv is None else _level(uv, UV_BANDS),
        "pollen": pollen[:3],
        "source": "Open-Meteo · CAMS",
    }


async def fetch(latitude: float, longitude: float, us_scale: bool = False) -> dict:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(URL, params=build_params(latitude, longitude))
        response.raise_for_status()
        return parse(response.json(), us_scale)
