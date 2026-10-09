from datetime import UTC, date, datetime

from beranda.providers import countries, creole, fullmoons, jieqi, matarii, methali, ritu, seasons


def test_solar_terms_fall_on_their_known_dates():
    known = {date(2026, 2, 4): "立春", date(2026, 4, 5): "清明", date(2026, 6, 21): "夏至",
             date(2026, 10, 8): "寒露", date(2026, 12, 22): "冬至"}
    for day, name in known.items():
        assert jieqi.current(day)["glyph"] == name, day
    assert jieqi.current(date(2026, 10, 7))["glyph"] == "秋分"
    assert jieqi.current(date(2026, 10, 9))["next_change"] == "2026-10-23"


def test_sun_longitude_at_the_equinox():
    lon = jieqi.sun_longitude(datetime(2026, 9, 23, 0, 5, tzinfo=UTC))
    assert min(lon, 360 - lon) > 179 and abs(lon - 180) < 0.1


def test_full_moon_names():
    assert fullmoons.current(date(2026, 10, 9), "America/New_York")["title"]["en"] == "Hunter's Moon"
    assert fullmoons.current(date(2026, 9, 10), "America/New_York")["title"]["en"] == "Harvest Moon"
    # in 2025 the full moon closest to the equinox fell in October
    assert fullmoons.current(date(2025, 10, 1), "America/New_York")["title"]["en"] == "Harvest Moon"
    assert fullmoons.current(date(2026, 12, 1), "America/New_York")["title"]["en"] == "Cold Moon"


def test_tithi_and_ritu():
    assert ritu.tithi(0.01)[1] == "Śukla Pratipadā"
    assert ritu.tithi(0.49)[1] == "Śukla Pūrṇimā"
    assert ritu.tithi(0.99)[1] == "Kṛṣṇa Amāvasyā"
    block = ritu.current(date(2026, 10, 9), 0.9)
    assert block["glyph"] == "शरद" and block["next_change"] == "2026-11-15"
    assert ritu.current(date(2026, 1, 5), 0.2)["glyph"] == "हेमंत"


def test_tahitian_seasons():
    assert matarii.current(date(2026, 10, 9))["title"]["en"] == "Matari'i i raro"
    assert matarii.current(date(2026, 12, 1))["title"]["en"] == "Matari'i i ni'a"
    assert matarii.current(date(2026, 3, 1))["next_change"] == "2026-05-20"


def test_creole_seasons_both_hemispheres():
    assert creole.current(date(2026, 10, 9), 18.5)["title"]["ht"] == "Sezon lapli"
    assert creole.current(date(2026, 2, 1), 16.2)["title"]["ht"] == "Sezon sèk"
    assert creole.current(date(2026, 2, 1), -21.1)["title"]["ht"] == "Sezon siklòn"
    assert creole.current(date(2026, 7, 1), -21.1)["next_change"] == "2026-11-15"


def test_daily_sayings_change_every_day():
    assert methali.current(date(2026, 10, 9))["title"] != methali.current(date(2026, 10, 10))["title"]
    assert len(methali.METHALI) >= 15 and len(creole.PWOVEB) >= 10


def test_hijri_block_is_left_to_the_display():
    block = seasons.current("arab", date(2026, 10, 9))
    assert block["kind"] == "hijri" and block["glyph"] == ""


def test_every_country_has_a_known_region_and_languages():
    for code, region in countries.REGION_OF.items():
        assert region in countries.REGION_NAMES, code
        assert countries.COUNTRY_LANGUAGES[code], code
        assert all(lang in countries.LANGUAGES for lang in countries.COUNTRY_LANGUAGES[code]), code
    assert countries.suggested_language("BR") == "pt-BR" and countries.suggested_language("HT") == "ht"
    assert countries.suggested_language("ZZ") == "en"
