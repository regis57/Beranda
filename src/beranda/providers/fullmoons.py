"""North American theme: the traditional names of the full moons.

The names are those printed by North American almanacs, drawn from Native American,
colonial and European traditions. The Harvest Moon is the full moon closest to the
September equinox; the Hunter's Moon is the one after it.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import astro, equinox

# month -> (English, French, meaning in English, meaning in French)
NAMES = {
    1: ("Wolf Moon", "Lune du loup", "Wolves howl in the deep of winter", "Les loups hurlent au cœur de l'hiver"),
    2: ("Snow Moon", "Lune des neiges", "The heaviest snows of the year", "Les plus fortes neiges de l'année"),
    3: ("Worm Moon", "Lune des vers", "The ground thaws, earthworms return", "Le sol dégèle, les vers reviennent"),
    4: ("Pink Moon", "Lune rose", "Wild pink phlox blooms", "Le phlox sauvage fleurit en rose"),
    5: ("Flower Moon", "Lune des fleurs", "Flowers everywhere", "Des fleurs partout"),
    6: ("Strawberry Moon", "Lune des fraises", "Wild strawberries ripen", "Les fraises des bois mûrissent"),
    7: ("Buck Moon", "Lune du cerf", "Bucks grow new antlers", "Les cerfs refont leurs bois"),
    8: ("Sturgeon Moon", "Lune de l'esturgeon", "Sturgeon fill the Great Lakes", "Les esturgeons emplissent les Grands Lacs"),
    9: ("Corn Moon", "Lune du maïs", "Corn is gathered", "On récolte le maïs"),
    10: ("Hunter's Moon", "Lune du chasseur", "Hunting by moonlight before winter", "On chasse au clair de lune avant l'hiver"),
    11: ("Beaver Moon", "Lune du castor", "Beavers finish their winter dams", "Les castors achèvent leurs barrages d'hiver"),
    12: ("Cold Moon", "Lune froide", "The longest, coldest nights", "Les nuits les plus longues et les plus froides"),
}
HARVEST = ("Harvest Moon", "Lune des moissons", "Light enough to harvest late into the night",
           "Assez de lumière pour moissonner tard le soir")
HUNTER = NAMES[10]


def _full_moons_around(when: datetime) -> list[datetime]:
    year = when.year + (when.timetuple().tm_yday - 1) / 365.25
    k0 = math.floor((year - 2000) * 12.3685) - 2
    return [astro.phase_event(k + 0.5) for k in range(k0, k0 + 6)]


def next_full_moon(now: datetime) -> datetime:
    return min(f for f in _full_moons_around(now) if f >= now)


def name_of(full: datetime, tz: str) -> tuple[str, str, str, str]:
    local = full.astimezone(ZoneInfo(tz))
    equinox_day = equinox.instant(local.year, "september")
    near = min(_full_moons_around(equinox_day), key=lambda f: abs(f - equinox_day))
    if abs((full - near).total_seconds()) < 86400:
        return HARVEST
    following = min(f for f in _full_moons_around(near) if f > near + timedelta(days=20))
    if abs((full - following).total_seconds()) < 86400:
        return HUNTER
    if local.month in (9, 10):  # the September or October moon that is neither: plain names
        return NAMES[9] if local.month == 9 else NAMES[10]
    return NAMES[local.month]


def current(today: date, tz: str) -> dict:
    now = datetime(today.year, today.month, today.day, 12, tzinfo=ZoneInfo(tz)).astimezone(UTC)
    full = next_full_moon(now)
    en, fr, mean_en, mean_fr = name_of(full, tz)
    local = full.astimezone(ZoneInfo(tz)).date()
    return {
        "kind": "fullmoon",
        "number": local.month,
        "glyph": f"{local.day:02d}",
        "seal": "○",
        "title": {"en": en, "fr": fr},
        "sub": {"en": mean_en, "fr": mean_fr},
        "note": None,  # the display writes "Full moon <date>" in the reader's language
        "next_change": local.isoformat(),
        "days_left": None,
    }
