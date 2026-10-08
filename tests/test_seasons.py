from datetime import date

from beranda.providers import pranata, republican, seasons


def test_republican_year_starts_on_the_paris_autumn_equinox():
    assert republican.autumn_equinox(2023) == date(2023, 9, 23)
    assert republican.autumn_equinox(2024) == date(2024, 9, 22)
    assert republican.autumn_equinox(2025) == date(2025, 9, 22)
    assert republican.autumn_equinox(2026) == date(2026, 9, 23)


def test_republican_day_names_cover_twelve_months_of_thirty_days():
    assert len(republican.DAY_NAMES) == 12
    assert all(len(month) == 30 for month in republican.DAY_NAMES)
    assert len({name for month in republican.DAY_NAMES for name in month}) == 360


def test_republican_known_days():
    first = republican.current(date(2026, 9, 23))
    assert first["title"]["fr"] == "1 Vendémiaire" and first["sub"]["fr"] == "Raisin"
    assert first["note"].endswith("An CCXXXV")
    today = republican.current(date(2026, 10, 8))
    assert today["title"]["fr"] == "16 Vendémiaire" and today["sub"]["fr"] == "Belle de nuit"
    assert "Sextidi" in today["note"]
    assert republican.current(date(2026, 10, 23))["title"]["fr"] == "1 Brumaire"


def test_republican_complementary_days_and_year_before_the_equinox():
    extra = republican.current(date(2027, 9, 18))
    assert extra["sub"]["fr"] == "Jour de la Vertu" and extra["note"] == "An CCXXXV"
    before = republican.current(date(2026, 9, 22))
    assert before["note"].endswith("An CCXXXIV")


def test_pranata_mangsa_boundaries():
    assert pranata.current(date(2026, 10, 8))["title"]["id"] == "Mangsa Kapat"
    assert pranata.current(date(2026, 10, 13))["title"]["id"] == "Mangsa Kalima"
    assert pranata.current(date(2026, 1, 10))["title"]["id"] == "Mangsa Kapitu"  # wraps over new year
    assert pranata.current(date(2028, 2, 29))["title"]["id"] == "Mangsa Kawolu"  # leap day
    assert pranata.current(date(2026, 6, 21))["title"]["id"] == "Mangsa Saddha"
    assert pranata.current(date(2026, 6, 22))["title"]["id"] == "Mangsa Kasa"


def test_pranata_days_left_counts_to_the_next_mangsa():
    assert pranata.current(date(2026, 10, 8))["days_left"] == 5


def test_every_day_of_a_year_has_a_season_in_every_theme():
    from datetime import timedelta

    day = date(2027, 1, 1)
    while day.year == 2027:
        for theme in ("japan", "indonesia", "france"):
            s = seasons.current(theme, day)
            assert s["glyph"] and s["title"]["fr"] and s["kind"]
        day += timedelta(days=1)


def test_unknown_theme_falls_back_to_japan():
    assert seasons.current("nope", date(2026, 10, 8))["kind"] == "ko"
