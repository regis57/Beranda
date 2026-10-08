"""Offline demo data, used for screenshots and for trying Beranda without any setup.

Everything that depends on the date (moon, sunrise, micro-season, public holidays) is
real; only the weather and the agenda below are invented. The display says "demo" so
nobody mistakes it for a forecast.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from ..config import KeyDate

# A believable week of autumn weather: (WMO code, tmax, tmin, rain mm, rain probability %)
_WEEK = (
    (3, 14, 8, 0.4, 35),
    (61, 13, 9, 4.2, 80),
    (80, 12, 8, 2.1, 65),
    (3, 12, 7, 0.0, 15),
    (1, 15, 6, 0.0, 5),
    (0, 17, 7, 0.0, 0),
    (2, 16, 9, 0.3, 25),
)


def weather(today: date, now: datetime, units: str = "metric") -> dict:
    def conv(c: int) -> int:
        return round(c * 9 / 5 + 32) if units == "imperial" else c

    days = []
    for i, (code, tmax, tmin, rain, pop) in enumerate(_WEEK):
        day = today + timedelta(days=i)
        days.append(
            {
                "date": day.isoformat(),
                "code": code,
                "tmax": conv(tmax),
                "tmin": conv(tmin),
                "precip": rain,
                "pop": pop,
                "sunrise": f"{day.isoformat()}T07:52",
                "sunset": f"{day.isoformat()}T18:55",
                "uv": 2.0,
            }
        )
    return {
        "current": {
            "time": now.replace(second=0, microsecond=0).isoformat(timespec="minutes"),
            "temp": conv(11),
            "feels": conv(9),
            "humidity": 78,
            "wind": 14 if units != "imperial" else 9,
            "wind_dir": 225,
            "code": 3,
            "is_day": 7 <= now.hour < 19,
            "precip": 0.0,
        },
        # light rain arriving in about 45 minutes, heaviest around an hour from now
        "rain": {
            "intervals": [0.0, 0.0, 0.0, 0.2, 0.5, 0.9, 0.6, 0.3],
            "raining_now": False,
            "starts_in_min": 45,
            "stops_in_min": None,
        },
        "daily": days,
        "units": (
            {"temp": "°F", "wind": "mph", "precip": "in"}
            if units == "imperial"
            else {"temp": "°C", "wind": "km/h", "precip": "mm"}
        ),
        "fetched_at": now.isoformat(timespec="seconds"),
        "source": "demo",
    }


def events(today: date, tz_offset_iso: str) -> list[dict]:
    """A few invented agenda entries relative to today. `tz_offset_iso` like '+02:00'."""

    def at(offset_days: int, hh: int, mm: int = 0) -> str:
        d = today + timedelta(days=offset_days)
        return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00{tz_offset_iso}"

    return [
        {"title": "Yoga", "start": at(0, 18, 30), "end": at(0, 19, 30), "all_day": False, "calendar": 0},
        {"title": "Dentiste", "start": at(1, 9, 15), "end": at(1, 10), "all_day": False, "calendar": 0},
        {"title": "Dîner chez Sam", "start": at(3, 20), "end": at(3, 22, 30), "all_day": False, "calendar": 0},
        {"title": "Marché", "start": at(4, 8), "end": at(4, 12), "all_day": False, "calendar": 0},
        {
            "title": "Week-end en Alsace",
            "start": f"{(today + timedelta(days=5)).isoformat()}T00:00:00{tz_offset_iso}",
            "end": f"{(today + timedelta(days=7)).isoformat()}T00:00:00{tz_offset_iso}",
            "all_day": True,
            "calendar": 0,
        },
    ]


def key_dates(today: date) -> tuple[KeyDate, ...]:
    """Invented personal dates falling inside the next few weeks."""
    a = today + timedelta(days=3)
    b = today + timedelta(days=11)
    c = today + timedelta(days=17)
    return (
        KeyDate(a.month, a.day, "Anniversaire de Léa", "birth", a.year - 8),
        KeyDate(b.month, b.day, "Souvenir de Papi", "death", b.year - 12),
        KeyDate(c.month, c.day, "Anniversaire de mariage", "anniversary", c.year - 6),
    )
