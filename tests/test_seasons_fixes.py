"""Regression tests for the seasons group: tithi, white-night sun times, holidays."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from beranda import config
from beranda.providers import astro, jieqi, ritu, specialdays

IST = ZoneInfo("Asia/Kolkata")


def test_tithi_follows_the_elongation_not_the_clock():
    # Checked against the Moon-Sun elongation: 76.5 deg is Saptami, 111.97 deg is still Dasami.
    dec16 = ritu.current(date(2026, 12, 16), datetime(2026, 12, 16, 7, tzinfo=IST))
    dec19 = ritu.current(date(2026, 12, 19), datetime(2026, 12, 19, 7, tzinfo=IST))
    assert dec16["sub"]["en"].endswith("Śukla Saptamī")
    assert dec19["sub"]["en"].endswith("Śukla Daśamī")


def test_moon_longitude_is_opposite_the_sun_at_full_moon():
    full = datetime(2026, 10, 26, 4, 12, tzinfo=UTC)
    gap = (astro.moon_longitude(full) - jieqi.sun_longitude(full)) % 360
    assert abs(gap - 180) < 0.5


def _minutes(times):
    rise = datetime.fromisoformat(times["sunrise"])
    sunset = datetime.fromisoformat(times["sunset"])
    return (sunset - rise) / timedelta(minutes=1)


def test_white_nights_still_have_a_sunrise_and_sunset():
    times = astro.sun_times(datetime(2026, 6, 21, 12, tzinfo=UTC), 61.50, 23.76, "Europe/Helsinki")
    assert times["sunrise"] and times["sunset"]
    assert abs(_minutes(times) - 1169) < 10


def test_sunset_after_midnight_keeps_the_day_length_positive():
    times = astro.sun_times(datetime(2026, 6, 21, 12, tzinfo=UTC), 64.15, -21.94, "Atlantic/Reykjavik")
    assert times["sunrise"] and times["sunset"]
    assert 20 * 60 < _minutes(times) < 22 * 60


def test_unknown_region_falls_back_to_national_holidays():
    cfg = config.from_dict({"country": "FR", "language": "fr", "subdivision": "moselle"})
    days = specialdays.special_days(cfg, date(2026, 12, 1), date(2027, 1, 31))
    assert "2026-12-25" in {d["date"] for d in days}


def test_ukraine_has_its_national_holidays():
    assert len(specialdays.public_holidays("UA", None, "uk", [2026])) > 0
