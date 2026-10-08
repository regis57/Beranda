from dataclasses import replace
from datetime import date

from beranda.config import Config, KeyDate
from beranda.providers import specialdays


def cfg(**kw) -> Config:
    return replace(Config(), **kw)


def test_public_holidays_in_french_for_france():
    days = specialdays.special_days(cfg(), date(2026, 11, 1), date(2026, 11, 30))
    labels = {d["date"]: d["label"] for d in days if d["kind"] == "holiday"}
    assert labels["2026-11-01"] == "Toussaint"
    assert labels["2026-11-11"] == "Armistice"


def test_other_country_and_language():
    days = specialdays.special_days(
        cfg(country="US", language="en"), date(2026, 7, 1), date(2026, 7, 10)
    )
    assert any(d["date"] == "2026-07-04" and "Independence" in d["label"] for d in days)


def test_unknown_country_does_not_crash():
    assert specialdays.special_days(cfg(country="ZZ"), date(2026, 1, 1), date(2026, 1, 31)) == []


def test_unsupported_language_falls_back_to_the_default():
    days = specialdays.special_days(
        cfg(country="JP", language="xx"), date(2026, 1, 1), date(2026, 1, 3)
    )
    assert any(d["date"] == "2026-01-01" for d in days)


def test_key_dates_show_the_number_of_years():
    keys = (KeyDate(10, 11, "Léa", "birth", 2018), KeyDate(10, 12, "Fête", "other"))
    days = specialdays.special_days(cfg(key_dates=keys), date(2026, 10, 1), date(2026, 10, 31))
    mine = {d["date"]: d for d in days if d["kind"] != "holiday"}
    assert mine["2026-10-11"]["label"] == "Léa (8)" and mine["2026-10-11"]["kind"] == "birth"
    assert mine["2026-10-12"]["label"] == "Fête"


def test_leap_day_is_skipped_in_common_years_and_kept_in_leap_years():
    keys = (KeyDate(2, 29, "Bissextile", "birth", 2000),)
    assert not [d for d in specialdays.special_days(cfg(key_dates=keys), date(2027, 2, 1), date(2027, 3, 1)) if d["kind"] == "birth"]
    leap = specialdays.special_days(cfg(key_dates=keys), date(2028, 2, 1), date(2028, 3, 1))
    assert any(d["date"] == "2028-02-29" for d in leap)


def test_window_spanning_new_year():
    keys = (KeyDate(1, 2, "Jan", "other"), KeyDate(12, 30, "Dec", "other"))
    days = specialdays.special_days(cfg(key_dates=keys), date(2026, 12, 15), date(2027, 1, 31))
    assert {d["label"] for d in days if d["kind"] == "other"} == {"Jan", "Dec"}


def test_holiday_sorts_before_personal_date_on_the_same_day():
    keys = (KeyDate(11, 1, "Perso", "birth"),)
    days = specialdays.special_days(cfg(key_dates=keys), date(2026, 11, 1), date(2026, 11, 1))
    assert [d["kind"] for d in days] == ["holiday", "birth"]
