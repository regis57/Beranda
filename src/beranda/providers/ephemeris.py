"""The "ephemeris": small facts about today that depend on where you live.

* the length of the day and how much it grew or shrank since yesterday (computed here);
* the name day ("saint of the day") in the countries that have one, from the free
  nameday.abalin.net service;
* the local calendar (Hijri, Persian, Hebrew, Buddhist era, Japanese era and rokuyo, Chinese
  lunar, Javanese pasaran...), which the page works out itself with the browser's calendars.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from . import astro

USER_AGENT = "Beranda/0.14 (+https://github.com/regis57/Beranda)"
NAMEDAY_URL = "https://nameday.abalin.net/api/V2/date"
# Countries that have a name-day calendar in the service (Russia is left out on purpose).
NAMEDAY_COUNTRIES = {
    "AT", "BG", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IT", "LT", "LV", "PL",
    "SE", "SK", "US",
}


def has_nameday(country: str) -> bool:
    return (country or "").upper() in NAMEDAY_COUNTRIES


def _find(node, key: str):
    """The first dict stored under `key`, however deep: the service nests its answer."""
    if isinstance(node, dict):
        if isinstance(node.get(key), dict):
            return node[key]
        for value in node.values():
            found = _find(value, key)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find(value, key)
            if found is not None:
                return found
    return None


def parse_nameday(payload: dict, country: str) -> str | None:
    """The names of the day for `country`. The service answers {"data": {"fr": "Ghislain", ...}}
    (older answers nested them under "namedays"); "n/a" means none today."""
    code = (country or "").lower()
    names = _find(payload, "namedays") or {}
    if not isinstance(names.get(code), str):
        data = payload.get("data") if isinstance(payload, dict) else None
        names = data if isinstance(data, dict) else {}
    text = names.get(code)
    if not isinstance(text, str) or text.strip().lower() in ("n/a", "-", ""):
        return None
    cleaned = ", ".join(part.strip() for part in text.split(",") if part.strip())
    return cleaned or None


async def fetch_nameday(country: str, month: int, day: int) -> str | None:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(NAMEDAY_URL, params={"day": day, "month": month})
        response.raise_for_status()
        return parse_nameday(response.json(), country)


def daylight(when: datetime, latitude: float, longitude: float, tz: str) -> dict:
    """Minutes of daylight today, and the change in seconds since yesterday (None near the poles)."""

    def minutes(moment: datetime) -> float | None:
        times = astro.sun_times(moment, latitude, longitude, tz)
        if not times["sunrise"] or not times["sunset"]:
            return None
        return (datetime.fromisoformat(times["sunset"]) - datetime.fromisoformat(times["sunrise"])).total_seconds() / 60

    today = minutes(when)
    yesterday = minutes(when - timedelta(days=1))
    return {
        "daylight_min": None if today is None else round(today),
        "delta_s": None if today is None or yesterday is None else round((today - yesterday) * 60),
    }
