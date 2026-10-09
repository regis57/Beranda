"""Moon and sun, computed locally: no network, no API key, works offline.

New and full moons use the leading terms of Jean Meeus, "Astronomical Algorithms" (ch. 49),
good to a few minutes. The phase fraction is measured between the real surrounding new
moons, so it never drifts from the calendar. Sun times and elevation come from `astral`.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import elevation, sun

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
    """Sunrise/sunset for the local date of `when`. Both None during polar day/night."""
    zone = ZoneInfo(tz)
    local = when.astimezone(zone)
    info = _observer(latitude, longitude, tz)
    try:
        times = sun(info.observer, date=local.date(), tzinfo=zone)
        return {
            "sunrise": times["sunrise"].isoformat(),
            "sunset": times["sunset"].isoformat(),
        }
    except ValueError:  # the sun never rises or never sets today
        return {"sunrise": None, "sunset": None}


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
