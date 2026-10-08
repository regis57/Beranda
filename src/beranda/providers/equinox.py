"""Equinoxes and solstices (Meeus, Astronomical Algorithms, ch. 27: mean values, valid for
the years 1000-3000 and good to within about half an hour, plenty for naming a day)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

# Polynomials in Y = (year - 2000) / 1000, giving the Julian Ephemeris Day.
_TERMS = {
    "march": (2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057),
    "june": (2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030),
    "september": (2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078),
    "december": (2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032),
}


def instant(year: int, which: str) -> datetime:
    """The UTC moment of an equinox ('march', 'september') or solstice ('june', 'december')."""
    y = (year - 2000) / 1000
    a, b, c, d, e = _TERMS[which]
    jde = a + b * y + c * y**2 + d * y**3 + e * y**4
    # JDE 2451545.0 is 2000-01-01 12:00 TT; TT runs about 69 s ahead of UTC.
    return datetime(2000, 1, 1, 12, tzinfo=UTC) + timedelta(days=jde - 2451545.0, seconds=-69)


def local_day(year: int, which: str, tz: str) -> date:
    return instant(year, which).astimezone(ZoneInfo(tz)).date()


# Which season starts at each event, north of the equator. South of it, they swap.
_NORTH = {"march": "spring", "june": "summer", "september": "autumn", "december": "winter"}
_SWAP = {"spring": "autumn", "summer": "winter", "autumn": "spring", "winter": "summer"}


def season(today: date, tz: str, latitude: float) -> dict:
    """The astronomical season in force today, for this hemisphere, and its next change."""
    events = []
    for year in (today.year - 1, today.year, today.year + 1):
        for which in ("march", "june", "september", "december"):
            events.append((local_day(year, which, tz), which))
    events.sort()
    current = max(e for e in events if e[0] <= today)
    upcoming = min(e for e in events if e[0] > today)
    name = _NORTH[current[1]]
    if latitude < 0:
        name = _SWAP[name]
    return {
        "season": name,
        "started": current[0].isoformat(),
        "next_change": upcoming[0].isoformat(),
        "days_left": (upcoming[0] - today).days,
    }
