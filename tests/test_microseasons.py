from datetime import date, timedelta

from beranda.providers import microseasons as ms


def test_there_are_exactly_72():
    assert len(ms.KO) == 72
    assert len({entry[2] for entry in ms.KO}) == 72  # every kanji name is distinct


def test_starts_are_in_calendar_order_from_risshun():
    # From Feb 4 the table must advance through the year, wrapping once at Jan 1.
    dates = [(m, d) for m, d, *_ in ms.KO]
    wrap = next(i for i in range(1, 72) if dates[i] < dates[i - 1])
    assert dates[wrap] == (1, 1)
    assert dates[:wrap] == sorted(dates[:wrap]) and dates[wrap:] == sorted(dates[wrap:])


def test_known_dates():
    assert ms.current(date(2026, 10, 8))["kanji"] == "鴻雁来"
    assert ms.current(date(2026, 2, 4))["number"] == 1  # start of spring
    assert ms.current(date(2026, 3, 26))["kanji"] == "桜始開"  # first cherry blossoms


def test_year_boundary_wraps():
    assert ms.current(date(2026, 1, 2))["kanji"] == "雪下出麦"
    assert ms.current(date(2026, 2, 3))["number"] == 72
    assert ms.current(date(2026, 12, 31))["kanji"] == "麋角解"


def test_every_day_of_a_leap_year_resolves_and_looks_ahead():
    day = date(2028, 1, 1)
    while day.year == 2028:
        info = ms.current(day)
        assert 1 <= info["number"] <= 72
        assert 1 <= info["days_left"] <= 7  # each lasts 5-6 days
        assert date.fromisoformat(info["next_change"]) == day + timedelta(days=info["days_left"])
        day += timedelta(days=1)
