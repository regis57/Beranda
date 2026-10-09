"""World radio: Radio Browser (radio-browser.info), a free, keyless directory of ~50,000
stations maintained by volunteers. No account, no clicks counted against the user.

Radio Browser runs on several independent, mirrored servers so that no single one is a
point of failure; a client is expected to try more than one. We keep a short, fixed list
of well-known mirrors and move to the next one if a request fails.
"""

from __future__ import annotations

import httpx

USER_AGENT = "Beranda/0.5 (+https://github.com/regis57/Beranda)"
MIRRORS = (
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
)
MAX_RESULTS = 30


def _station(raw: dict) -> dict:
    return {
        "uuid": raw.get("stationuuid", ""),
        "name": raw.get("name", "").strip() or "?",
        "url": raw.get("url_resolved") or raw.get("url", ""),
        "favicon": raw.get("favicon", ""),
        "country": raw.get("countrycode", ""),
        "language": (raw.get("language", "") or "").split(",")[0].strip(),
        "tags": [t for t in (raw.get("tags", "") or "").split(",") if t][:3],
    }


async def search(
    *, country: str = "", language: str = "", name: str = "", tag: str = "", limit: int = MAX_RESULTS
) -> list[dict]:
    """Stations matching any of the given filters, most popular first."""
    params = {
        "limit": min(limit, MAX_RESULTS),
        "hidebroken": "true",
        "order": "clickcount",
        "reverse": "true",
    }
    if country:
        params["countrycode"] = country.upper()
    if language:
        params["language"] = language
    if name:
        params["name"] = name
    if tag:
        params["tag"] = tag

    last_error: Exception | None = None
    for mirror in MIRRORS:
        try:
            async with httpx.AsyncClient(timeout=8, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get(f"{mirror}/json/stations/search", params=params)
                r.raise_for_status()
                return [_station(s) for s in r.json()]
        except httpx.HTTPError as exc:
            last_error = exc
            continue
    raise last_error or RuntimeError("no radio mirror reachable")
