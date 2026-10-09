"""Official weather warnings in Europe, from MeteoAlarm's public Atom feed (no key).

MeteoAlarm publishes one feed per country, listing only the warnings that are active (one
entry per warned area). We keep the ones for the area the user typed (a department, a county,
a region: the name MeteoAlarm uses). Outside Europe there is no equivalent single free source,
so the widget simply stays empty there.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta

import httpx
from defusedxml.ElementTree import fromstring

USER_AGENT = "Beranda/0.14 (+https://github.com/regis57/Beranda)"
FEED = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-{slug}"

# ISO country code -> the name MeteoAlarm uses in its feed addresses.
SLUGS = {
    "AT": "austria", "BE": "belgium", "BA": "bosnia-herzegovina", "BG": "bulgaria", "HR": "croatia",
    "CY": "cyprus", "CZ": "czechia", "DK": "denmark", "EE": "estonia", "FI": "finland",
    "FR": "france", "DE": "germany", "GR": "greece", "HU": "hungary", "IS": "iceland",
    "IE": "ireland", "IL": "israel", "IT": "italy", "LV": "latvia", "LT": "lithuania",
    "LU": "luxembourg", "MT": "malta", "MD": "moldova", "ME": "montenegro", "NL": "netherlands",
    "MK": "north-macedonia", "NO": "norway", "PL": "poland", "PT": "portugal", "RO": "romania",
    "RS": "serbia", "SK": "slovakia", "SI": "slovenia", "ES": "spain", "SE": "sweden",
    "CH": "switzerland", "UA": "ukraine", "GB": "united-kingdom",
}

# (words in the event text, our own short kind) - first match wins, so specific ones come first.
KINDS = (
    ("thunder", "thunderstorm"), ("flood", "flood"), ("avalanche", "avalanche"), ("forest", "fire"),
    ("fire", "fire"), ("coastal", "coastal"), ("snow", "snow_ice"), ("ice", "snow_ice"),
    ("fog", "fog"), ("wind", "wind"), ("rain", "rain"), ("high temperature", "heat"),
    ("heat", "heat"), ("low temperature", "cold"), ("cold", "cold"),
)
COLOURS = {"yellow": 1, "orange": 2, "red": 3}
SEVERITY = {"moderate": 1, "severe": 2, "extreme": 3}  # MeteoAlarm: yellow / orange / red


def supported(country: str) -> bool:
    return (country or "").upper() in SLUGS


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _norm(text: str) -> str:
    stripped = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(stripped.lower().replace("-", " ").split())


def _when(raw: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(raw or "")
    except ValueError:
        return None


def _kind(event: str) -> str:
    low = event.lower()
    return next((kind for word, kind in KINDS if word in low), "other")


def parse(xml_text: str, now: datetime) -> list[dict]:
    """Every active warning in the feed: {area, kind, level 1-3, event, onset, expires}."""
    root = fromstring(xml_text.encode("utf-8"), forbid_dtd=True)
    out = []
    for entry in root:
        if _local(entry.tag) != "entry":
            continue
        fields = {_local(child.tag): (child.text or "").strip() for child in entry if child.text}
        title = fields.get("title", "")
        level = COLOURS.get(title.split(" ", 1)[0].lower()) or SEVERITY.get(fields.get("severity", "").lower())
        expires, onset = _when(fields.get("expires")), _when(fields.get("onset"))
        if not level or not fields.get("areadesc"):
            continue
        if fields.get("status", "Actual") != "Actual":
            continue
        if expires and expires <= now:
            continue  # already over
        if onset and onset > now + timedelta(hours=24):
            continue  # not for today or tomorrow yet
        event = fields.get("event", title)
        out.append(
            {
                "area": fields["areadesc"],
                "kind": _kind(event),
                "level": level,
                "event": event,
                "onset": fields.get("onset", ""),
                "expires": fields.get("expires", ""),
            }
        )
    return out


def for_area(warnings: list[dict], area: str, limit: int = 3) -> list[dict]:
    """The warnings for the user's area (names compared without accents, case or hyphens),
    the worst of each kind only, most serious first."""
    wanted = _norm(area)
    if not wanted:
        return []
    mine = [w for w in warnings if wanted in _norm(w["area"]) or _norm(w["area"]) in wanted]
    worst: dict[str, dict] = {}
    for warning in mine:
        if warning["kind"] not in worst or warning["level"] > worst[warning["kind"]]["level"]:
            worst[warning["kind"]] = warning
    return sorted(worst.values(), key=lambda w: (-w["level"], w["kind"]))[:limit]


async def fetch(country: str, now: datetime) -> list[dict]:
    slug = SLUGS.get((country or "").upper())
    if slug is None:
        return []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(FEED.format(slug=slug))
        response.raise_for_status()
    return parse(response.text, now)
