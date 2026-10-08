from datetime import UTC, datetime

from beranda.providers import astro


def minutes_apart(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) / 60


def test_new_moon_matches_the_2026_solar_eclipses():
    # Solar eclipses only happen at new moon: 2026-02-17 ~12:01 UTC and 2026-08-12 ~17:37 UTC.
    _, _, feb = astro._surrounding_new_moons(datetime(2026, 2, 1, tzinfo=UTC))
    _, _, aug = astro._surrounding_new_moons(datetime(2026, 8, 1, tzinfo=UTC))
    assert minutes_apart(feb, datetime(2026, 2, 17, 12, 1, tzinfo=UTC)) < 20
    assert minutes_apart(aug, datetime(2026, 8, 12, 17, 37, tzinfo=UTC)) < 20


def test_full_moon_oct_2026():
    state = astro.moon(datetime(2026, 10, 8, 12, tzinfo=UTC), 49.0)
    full = datetime.fromisoformat(state["next_full"])
    assert minutes_apart(full, datetime(2026, 10, 26, 4, 12, tzinfo=UTC)) < 20


def test_phase_is_consistent_around_the_cycle():
    new = datetime(2026, 8, 12, 17, 38, tzinfo=UTC)
    just_after = astro.moon(new.replace(hour=19), 49.0)
    assert just_after["name"] == "new" and just_after["illumination"] < 0.01
    assert just_after["waxing"] is True

    full = astro.moon(datetime(2026, 8, 28, 4, 18, tzinfo=UTC), 49.0)  # full moon, Aug 2026
    assert full["name"] == "full"
    assert full["illumination"] > 0.98
    assert abs(full["phase"] - 0.5) < 0.02

    waning = astro.moon(datetime(2026, 9, 4, 12, tzinfo=UTC), 49.0)
    assert waning["waxing"] is False and waning["name"] in {"last_quarter", "waning_gibbous"}


def test_southern_hemisphere_is_mirrored():
    now = datetime(2026, 10, 8, 12, tzinfo=UTC)
    assert astro.moon(now, -33.9)["mirrored"] is True
    assert astro.moon(now, 49.1)["mirrored"] is False


def test_night_follows_the_sun():
    paris = (49.1, 6.2)
    assert astro.is_night(datetime(2026, 10, 8, 22, 0, tzinfo=UTC), *paris) is True
    assert astro.is_night(datetime(2026, 10, 8, 11, 0, tzinfo=UTC), *paris) is False


def test_sun_times_handle_polar_night():
    # Tromsø around the winter solstice: the sun does not rise.
    times = astro.sun_times(
        datetime(2026, 12, 21, 12, tzinfo=UTC), 69.65, 18.96, "Europe/Oslo"
    )
    assert times == {"sunrise": None, "sunset": None}


def test_sun_times_normal_day():
    times = astro.sun_times(datetime(2026, 10, 8, 12, tzinfo=UTC), 49.12, 6.18, "Europe/Paris")
    assert times["sunrise"] < times["sunset"]
    assert times["sunrise"].startswith("2026-10-08T07:")
