"""The next prayer under the moon, in countries whose constitution makes Islam the state religion."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from beranda.providers import prayer

MECCA = (21.4225, 39.8262, "Asia/Riyadh")
CAIRO = (30.0444, 31.2357, "Africa/Cairo")
KARACHI = (24.8607, 67.0011, "Asia/Karachi")


def hm(moment):
    return moment.strftime("%H:%M")


def close(actual, expected, minutes=3):
    hours, mins = (int(x) for x in expected.split(":"))
    return abs((actual.hour * 60 + actual.minute) - (hours * 60 + mins)) <= minutes


@pytest.mark.parametrize(("country", "place", "day", "published"), [
    # Published timetables for these days (Umm al-Qura, Egyptian Survey Authority, Karachi),
    # within a few minutes: a mosque may round or add a precaution minute differently.
    ("SA", MECCA, date(2024, 3, 20), {"fajr": "05:10", "dhuhr": "12:29", "asr": "15:53", "maghrib": "18:32", "isha": "20:02"}),
    ("EG", CAIRO, date(2024, 6, 21), {"fajr": "04:08", "dhuhr": "12:58", "asr": "16:33", "maghrib": "19:59", "isha": "21:32"}),
    ("PK", KARACHI, date(2024, 1, 15), {"fajr": "05:58", "dhuhr": "12:42", "asr": "16:27", "maghrib": "18:04", "isha": "19:23"}),
])
def test_times_match_the_published_timetables(country, place, day, published):
    found = prayer.times(day, *place, country)
    for name, expected in published.items():
        assert close(found[name], expected), (country, name, hm(found[name]), expected)


def test_the_five_prayers_come_in_order():
    found = prayer.times(date(2026, 10, 18), *CAIRO, "EG")
    moments = [found[name] for name in prayer.PRAYERS]
    assert moments == sorted(moments)


def test_umm_al_qura_isha_is_ninety_minutes_after_sunset():
    found = prayer.times(date(2026, 10, 18), *MECCA, "SA")
    assert found["isha"] - found["maghrib"] == timedelta(minutes=90)


def test_hanafi_asr_comes_later():
    day = date(2026, 10, 18)
    hanafi = prayer.times(day, *KARACHI, "PK")["asr"]
    prayer.COUNTRIES["XX"] = prayer.MWL
    try:
        shafii = prayer.times(day, *KARACHI, "XX")["asr"]
    finally:
        del prayer.COUNTRIES["XX"]
    assert hanafi - shafii > timedelta(minutes=30)


def test_the_next_prayer_is_the_first_still_to_come():
    zone = ZoneInfo(CAIRO[2])
    found = prayer.times(date(2026, 10, 18), *CAIRO, "EG")
    just_after_dhuhr = found["dhuhr"] + timedelta(minutes=1)
    nxt = prayer.next_prayer(just_after_dhuhr.astimezone(zone), *CAIRO, "EG")
    assert nxt == {"name": "asr", "at": found["asr"].isoformat(timespec="minutes")}


def test_after_isha_the_next_is_tomorrows_fajr():
    found = prayer.times(date(2026, 10, 18), *CAIRO, "EG")
    nxt = prayer.next_prayer(found["isha"] + timedelta(minutes=5), *CAIRO, "EG")
    tomorrow = prayer.times(date(2026, 10, 19), *CAIRO, "EG")["fajr"]
    assert nxt == {"name": "fajr", "at": tomorrow.isoformat(timespec="minutes")}


@pytest.mark.parametrize("country", ["FR", "ID", "TR", "TN", "US", ""])
def test_nothing_outside_the_countries_that_declare_islam_their_religion(country):
    assert prayer.next_prayer(datetime(2026, 10, 18, 12, tzinfo=ZoneInfo("UTC")), *CAIRO, country) is None


def test_lower_case_country_codes_work():
    assert prayer.applies("ma") and prayer.applies("MA")


# ------------------------------------------------------------------ on the screen ---
def _state(tmp_path, **kw):
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from beranda.app import create_app
    from beranda.config import Config, Location

    now = datetime(2026, 10, 18, 13, 0, tzinfo=ZoneInfo("Africa/Casablanca"))
    cfg = replace(Config(), cache_dir=tmp_path / "cache", demo=True, news_enabled=False, history_enabled=False,
                  location=Location(name="Rabat", latitude=34.02, longitude=-6.84, timezone="Africa/Casablanca"), **kw)
    client = TestClient(create_app(cfg, now_fn=lambda: now), client=("127.0.0.1", 50000))
    return client.get("/api/state").json()


def test_the_screen_gets_the_next_prayer_in_morocco(tmp_path):
    sky = _state(tmp_path, country="MA")["sky"]
    assert sky["prayer"]["name"] in prayer.PRAYERS
    assert sky["prayer"]["at"].startswith("2026-10-18T") or sky["prayer"]["at"].startswith("2026-10-19T")


def test_the_screen_gets_no_prayer_in_france(tmp_path):
    assert _state(tmp_path, country="FR")["sky"]["prayer"] is None


def test_the_prayer_can_be_switched_off(tmp_path):
    assert _state(tmp_path, country="MA", widget_prayer=False)["sky"]["prayer"] is None


def test_the_switch_survives_the_settings_file():
    from beranda.config import Config, from_dict, to_dict

    cfg = from_dict(to_dict(Config(widget_prayer=False)))
    assert cfg.widget_prayer is False
    assert from_dict({}).widget_prayer is True
