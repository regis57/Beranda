"""Moon and sun, computed locally: no network, no API key, works offline.

New and full moons use the leading terms of Jean Meeus, "Astronomical Algorithms" (ch. 49),
good to a few minutes. The phase fraction is measured between the real surrounding new
moons, so it never drifts from the calendar. Sun times and elevation come from `astral`.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import elevation, sunrise, sunset

SYNODIC_MONTH = 29.530588861  # days, mean
_UNIX_EPOCH_JD = 2440587.5

# Below this sun elevation (degrees) we consider it night. -3 keeps a short dusk glow.
NIGHT_ELEVATION = -3.0

_PHASE_NAMES = (
    "new",
    "waxing_crescent",
    "first_quarter",
    "waxing_gibbous",
    "full",
    "waning_gibbous",
    "last_quarter",
    "waning_crescent",
)


def _jd_to_datetime(jd: float) -> datetime:
    return datetime.fromtimestamp((jd - _UNIX_EPOCH_JD) * 86400, tz=UTC)


def _sin(deg: float) -> float:
    return math.sin(math.radians(deg))


def _phase_event(k: float) -> datetime:
    """Instant of the new moon (k integer) or full moon (k + 0.5), Meeus ch. 49."""
    t = k / 1236.85
    jde = (
        2451550.09766
        + SYNODIC_MONTH * k
        + 0.00015437 * t**2
        - 0.000000150 * t**3
        + 0.00000000073 * t**4
    )
    e = 1 - 0.002516 * t - 0.0000074 * t**2
    m = 2.5534 + 29.10535670 * k - 0.0000014 * t**2 - 0.00000011 * t**3  # sun anomaly
    mp = (
        201.5643 + 385.81693528 * k + 0.0107582 * t**2 + 0.00001238 * t**3 - 0.000000058 * t**4
    )  # moon anomaly
    f = 160.7108 + 390.67050284 * k - 0.0016118 * t**2 - 0.00000227 * t**3 + 0.000000011 * t**4
    omega = 124.7746 - 1.56375588 * k + 0.0020672 * t**2 + 0.00000215 * t**3
    full = abs(k - round(k)) > 0.25
    c_mp, c_m, c_2mp, c_2f, c_mpm, c_mpm2 = (
        (-0.40614, 0.17302, 0.01614, 0.01043, 0.00734, -0.00515)
        if full
        else (-0.40720, 0.17241, 0.01608, 0.01039, 0.00739, -0.00514)
    )
    jde += (
        c_mp * _sin(mp)
        + c_m * e * _sin(m)
        + c_2mp * _sin(2 * mp)
        + c_2f * _sin(2 * f)
        + c_mpm * e * _sin(mp - m)
        + c_mpm2 * e * _sin(mp + m)
        + 0.00209 * e * e * _sin(2 * m)
        - 0.00111 * _sin(mp - 2 * f)
        - 0.00057 * _sin(mp + 2 * f)
        + 0.00056 * e * _sin(2 * mp + m)
        - 0.00042 * _sin(3 * mp)
        + 0.00042 * e * _sin(m + 2 * f)
        + 0.00038 * e * _sin(m - 2 * f)
        - 0.00024 * e * _sin(2 * mp - m)
        - 0.00017 * _sin(omega)
    )
    return _jd_to_datetime(jde)


def _surrounding_new_moons(when: datetime) -> tuple[float, datetime, datetime]:
    """(k, previous new moon, next new moon) around `when`."""
    when = when.astimezone(UTC)
    decimal_year = when.year + (when.timetuple().tm_yday - 1) / 365.25
    k = math.floor((decimal_year - 2000) * 12.3685)
    while _phase_event(k) > when:
        k -= 1
    while _phase_event(k + 1) <= when:
        k += 1
    return k, _phase_event(k), _phase_event(k + 1)


def moon(when: datetime, latitude: float) -> dict:
    """Moon state at `when`. `phase` is 0 (new) .. 0.5 (full) .. 1 (new again).

    New moon to full moon and full moon to the next new moon are measured separately
    (the two halves of a lunation differ by up to a day), so a full moon is exactly 0.5.
    """
    k, previous_new, next_new = _surrounding_new_moons(when)
    when_utc = when.astimezone(UTC)
    full = _phase_event(k + 0.5)

    def days(a: datetime, b: datetime) -> float:
        return (b - a).total_seconds() / 86400

    age = days(previous_new, when_utc)
    if when_utc < full:
        phase = 0.5 * days(previous_new, when_utc) / days(previous_new, full)
        next_full = full
    else:
        phase = 0.5 + 0.5 * days(full, when_utc) / days(full, next_new)
        next_full = _phase_event(k + 1.5)
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2
    name = _PHASE_NAMES[int(phase * 8 + 0.5) % 8]

    return {
        "phase": round(phase, 4),
        "age_days": round(age, 2),
        "illumination": round(illumination, 3),
        "name": name,
        "waxing": phase < 0.5,
        # Seen from the southern hemisphere the lit side is mirrored.
        "mirrored": latitude < 0,
        "next_full": next_full.isoformat(timespec="minutes"),
        "next_new": next_new.isoformat(timespec="minutes"),
    }


def _observer(latitude: float, longitude: float, tz: str):
    return LocationInfo("", "", tz, latitude, longitude)


def sun_times(when: datetime, latitude: float, longitude: float, tz: str) -> dict:
    """Sunrise/sunset for the local date of `when`, each None only if it does not happen today."""
    zone = ZoneInfo(tz)
    local = when.astimezone(zone)
    observer = _observer(latitude, longitude, tz).observer
    # Each event is asked for on its own: astral's sun() also wants civil dawn and dusk, and
    # during the white nights above about 60 degrees those never happen, which used to wipe
    # out a perfectly real sunrise and sunset for weeks every summer.
    try:
        rise = sunrise(observer, date=local.date(), tzinfo=zone)
    except ValueError:  # polar night or polar day
        rise = None
    try:
        down = sunset(observer, date=local.date(), tzinfo=zone)
    except ValueError:
        down = None
    if rise and down and down < rise:
        # When the sun sets after local midnight, astral gives the previous evening's sunset;
        # the one that ends today's daylight is the one dated tomorrow.
        try:
            down = sunset(observer, date=local.date() + timedelta(days=1), tzinfo=zone)
        except ValueError:
            down = None
    return {
        "sunrise": rise.isoformat() if rise else None,
        "sunset": down.isoformat() if down else None,
    }


# Main periodic terms of the Moon's longitude, Meeus "Astronomical Algorithms" table 47.A:
# (D, M, M', F, coefficient in millionths of a degree). The 25 largest terms give a few
# hundredths of a degree, far finer than the 12 degrees of an Indian lunar day.
_MOON_TERMS = (
    (0, 0, 1, 0, 6288774), (2, 0, -1, 0, 1274027), (2, 0, 0, 0, 658314), (0, 0, 2, 0, 213618),
    (0, 1, 0, 0, -185116), (0, 0, 0, 2, -114332), (2, 0, -2, 0, 58793), (2, -1, -1, 0, 57066),
    (2, 0, 1, 0, 53322), (2, -1, 0, 0, 45758), (0, 1, -1, 0, -40923), (1, 0, 0, 0, -34720),
    (0, 1, 1, 0, -30383), (2, 0, 0, -2, 15327), (0, 0, 1, 2, -12528), (0, 0, 1, -2, 10980),
    (4, 0, -1, 0, 10675), (0, 0, 3, 0, 10034), (4, 0, -2, 0, 8548), (2, 1, -1, 0, -7888),
    (2, 1, 0, 0, -6766), (1, 0, -1, 0, -5163), (1, 1, 0, 0, 4987), (2, -1, 1, 0, 4036),
    (2, 0, 2, 0, 3994),
)


def moon_longitude(when: datetime) -> float:
    """Apparent ecliptic longitude of the Moon, degrees (Meeus ch. 47, main terms)."""
    jd = when.astimezone(UTC).timestamp() / 86400 + _UNIX_EPOCH_JD
    t = (jd - 2451545.0) / 36525
    mean_lon = 218.3164477 + 481267.88123421 * t
    d = math.radians(297.8501921 + 445267.1114034 * t)
    m = math.radians(357.5291092 + 35999.0502909 * t)
    mp = math.radians(134.9633964 + 477198.8675055 * t)
    f = math.radians(93.2720950 + 483202.0175233 * t)
    # The Earth's orbit is slowly getting rounder, which weakens the terms that involve the
    # Sun's anomaly M; E is Meeus's correction for that.
    e = 1 - 0.002516 * t
    total = sum(
        coeff * e ** abs(km) * math.sin(kd * d + km * m + kmp * mp + kf * f)
        for kd, km, kmp, kf, coeff in _MOON_TERMS
    )
    a1 = math.radians(119.75 + 131.849 * t)
    a2 = math.radians(53.09 + 479264.290 * t)
    total += 3958 * math.sin(a1) + 1962 * math.sin(math.radians(mean_lon) - f) + 318 * math.sin(a2)
    omega = math.radians(125.04452 - 1934.136261 * t)
    return (mean_lon + total / 1e6 - 0.00478 * math.sin(omega)) % 360


def is_night(when: datetime, latitude: float, longitude: float) -> bool:
    info = _observer(latitude, longitude, "UTC")
    return elevation(info.observer, when.astimezone(UTC)) < NIGHT_ELEVATION


def astro(when: datetime, latitude: float, longitude: float, tz: str) -> dict:
    return {
        "moon": moon(when, latitude),
        "sun": sun_times(when, latitude, longitude, tz),
        "night": is_night(when, latitude, longitude),
    }


# Public name for other modules (full-moon names, etc.).
phase_event = _phase_event
