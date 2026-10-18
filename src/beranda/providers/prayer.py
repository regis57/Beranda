"""The next of the five daily prayers, worked out on the Pi from the sun - no web service.

Shown only in countries whose constitution makes Islam the religion of the state: those are
the countries that call themselves Muslim countries, and where a household is most likely to
want it on the wall. Elsewhere it simply does not appear.

Each country gets the calculation its own religious authority publishes (the same choices
the common prayer-time apps make): the sun's depth below the horizon that starts Fajr and
Isha, or a fixed time after sunset for Isha, and the shadow length for Asr. Times are
rounded to the minute and can differ from the local mosque's timetable by a minute or two.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from astral import Observer, SunDirection
from astral.sun import elevation, noon, sunset, time_at_elevation

PRAYERS = ("fajr", "dhuhr", "asr", "maghrib", "isha")


@dataclass(frozen=True)
class Method:
    fajr: float  # degrees below the horizon at dawn
    isha: float | None = None  # degrees below the horizon at nightfall...
    isha_minutes: int | None = None  # ...or minutes after sunset, where that is the rule
    maghrib: float | None = None  # degrees below the horizon; None = at sunset
    asr_shadow: int = 1  # 1: shadow as long as the object (most schools), 2: twice (Hanafi)


MWL = Method(18, 17)  # Muslim World League, the usual default
EGYPT = Method(19.5, 17.5)  # Egyptian General Authority of Survey
KARACHI = Method(18, 18, asr_shadow=2)  # University of Islamic Sciences, Karachi; Hanafi Asr
UMM_AL_QURA = Method(18.5, isha_minutes=90)  # Saudi Arabia's official calendar
GULF = Method(19.5, isha_minutes=90)
KUWAIT = Method(18, 17.5)
QATAR = Method(18, isha_minutes=90)
DUBAI = Method(18.2, 18.2)
TEHRAN = Method(17.7, 14, maghrib=4.5)  # Institute of Geophysics, University of Tehran
JAKIM = Method(20, 18)  # Malaysia and Brunei
MOROCCO = Method(19, 17)
ALGERIA = Method(18, 17)
JORDAN = Method(18, 18)

# Islam is the state religion in the constitution of each of these (ISO 3166-1 codes).
# Tunisia left out on purpose: its 2022 constitution no longer names a state religion.
COUNTRIES: dict[str, Method] = {
    "AF": KARACHI, "BD": KARACHI, "PK": KARACHI,
    "SA": UMM_AL_QURA, "BH": GULF, "OM": GULF, "YE": MWL,
    "KW": KUWAIT, "QA": QATAR, "AE": DUBAI,
    "IR": TEHRAN, "IQ": MWL, "JO": JORDAN, "PS": EGYPT,
    "EG": EGYPT, "LY": EGYPT, "DZ": ALGERIA, "MA": MOROCCO, "MR": MWL,
    "SO": MWL, "DJ": EGYPT, "KM": MWL,
    "MY": JAKIM, "BN": JAKIM, "MV": MWL,
}


def applies(country: str) -> bool:
    return country.upper() in COUNTRIES


def _round(moment: datetime) -> datetime:
    # Prayer timetables are printed to the minute; half a minute or more goes up.
    return (moment + timedelta(seconds=30)).replace(second=0, microsecond=0)


def times(day: date, latitude: float, longitude: float, tz: str, country: str) -> dict[str, datetime | None]:
    """The five prayers of `day`, local time. A prayer is None on the rare day the sun never
    gets low enough to mark it (far north in summer), rather than an invented time."""
    method = COUNTRIES[country.upper()]
    zone = ZoneInfo(tz)
    where = Observer(latitude, longitude)

    def below(angle: float, direction: SunDirection) -> datetime | None:
        try:
            return time_at_elevation(where, -angle, day, direction, tzinfo=zone)
        except ValueError:
            return None

    midday = noon(where, day, tzinfo=zone)
    # Asr begins when an object's shadow has grown by `asr_shadow` times its own length
    # beyond its shortest shadow at noon; from the sun's height at noon that is a fixed height.
    noon_height = math.radians(elevation(where, midday))
    shortest = 1 / math.tan(noon_height) if noon_height > 0 else math.inf
    asr_height = math.degrees(math.atan(1 / (method.asr_shadow + shortest)))
    try:
        asr = time_at_elevation(where, asr_height, day, SunDirection.SETTING, tzinfo=zone)
    except ValueError:
        asr = None
    try:
        sundown = sunset(where, day, tzinfo=zone)
    except ValueError:
        sundown = None
    maghrib = below(method.maghrib, SunDirection.SETTING) if method.maghrib else sundown
    if method.isha_minutes is not None:
        isha = sundown + timedelta(minutes=method.isha_minutes) if sundown else None
    else:
        isha = below(method.isha, SunDirection.SETTING)
    found = {
        "fajr": below(method.fajr, SunDirection.RISING),
        # A minute after the sun crosses the meridian, as timetables do, so Dhuhr never
        # starts while the sun is still at its height.
        "dhuhr": midday + timedelta(minutes=1),
        "asr": asr,
        "maghrib": maghrib,
        "isha": isha,
    }
    return {name: _round(at) if at else None for name, at in found.items()}


def next_prayer(now: datetime, latitude: float, longitude: float, tz: str, country: str) -> dict | None:
    """{"name": "asr", "at": iso} for the next prayer after `now`, or None outside the countries."""
    if not applies(country):
        return None
    local = now.astimezone(ZoneInfo(tz))
    for day in (local.date(), local.date() + timedelta(days=1)):
        for name, at in times(day, latitude, longitude, tz, country).items():
            if at and at > local:
                return {"name": name, "at": at.isoformat(timespec="minutes")}
    return None
