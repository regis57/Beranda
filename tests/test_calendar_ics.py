from datetime import date

import httpx
import pytest
import respx

from beranda.providers import calendar_ics as ics

SAMPLE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:one
DTSTAMP:20260101T000000Z
DTSTART:20261009T073000Z
DTEND:20261009T083000Z
SUMMARY:Dentiste
END:VEVENT
BEGIN:VEVENT
UID:two
DTSTAMP:20260101T000000Z
DTSTART;VALUE=DATE:20261010
DTEND;VALUE=DATE:20261012
SUMMARY:Week-end
END:VEVENT
BEGIN:VEVENT
UID:weekly
DTSTAMP:20260101T000000Z
DTSTART;TZID=Europe/Paris:20261006T183000
DTEND;TZID=Europe/Paris:20261006T193000
RRULE:FREQ=WEEKLY;COUNT=4
SUMMARY:Yoga
END:VEVENT
BEGIN:VEVENT
UID:outside
DTSTAMP:20260101T000000Z
DTSTART:20270601T100000Z
DTEND:20270601T110000Z
SUMMARY:Far away
END:VEVENT
END:VCALENDAR
"""

WINDOW = (date(2026, 10, 1), date(2026, 11, 30))


def test_timed_events_are_converted_to_local_time():
    events = ics.events_from_ics(SAMPLE, *WINDOW, "Europe/Paris")
    dentist = next(e for e in events if e["title"] == "Dentiste")
    assert dentist["start"] == "2026-10-09T09:30:00+02:00" and dentist["all_day"] is False


def test_all_day_events_keep_an_exclusive_end():
    events = ics.events_from_ics(SAMPLE, *WINDOW, "Europe/Paris")
    weekend = next(e for e in events if e["title"] == "Week-end")
    assert weekend["all_day"] is True
    assert weekend["start"].startswith("2026-10-10") and weekend["end"].startswith("2026-10-12")


def test_recurring_events_are_expanded_and_events_outside_the_window_dropped():
    events = ics.events_from_ics(SAMPLE, *WINDOW, "Europe/Paris")
    yoga = [e for e in events if e["title"] == "Yoga"]
    assert [e["start"][:10] for e in yoga] == ["2026-10-06", "2026-10-13", "2026-10-20", "2026-10-27"]
    # Daylight saving ends on 2026-10-25: the wall-clock time stays 18:30, the offset changes.
    assert all("T18:30:00" in e["start"] for e in yoga)
    assert [e["start"][-6:] for e in yoga] == ["+02:00", "+02:00", "+02:00", "+01:00"]
    assert not any(e["title"] == "Far away" for e in events)


def test_events_are_sorted():
    events = ics.events_from_ics(SAMPLE, *WINDOW, "Europe/Paris")
    assert [e["start"] for e in events] == sorted(e["start"] for e in events)


def test_webcal_scheme_is_rewritten():
    assert ics.normalise_url("webcal://p01-caldav.icloud.com/x.ics") == "https://p01-caldav.icloud.com/x.ics"
    assert ics.normalise_url("https://calendar.google.com/a.ics") == "https://calendar.google.com/a.ics"


@respx.mock
async def test_download_follows_redirects_and_returns_text():
    respx.get("https://example.org/a.ics").mock(
        return_value=httpx.Response(302, headers={"location": "https://example.org/b.ics"})
    )
    respx.get("https://example.org/b.ics").mock(return_value=httpx.Response(200, text=SAMPLE))
    assert "BEGIN:VCALENDAR" in await ics.download("https://example.org/a.ics")


@respx.mock
async def test_download_refuses_huge_files(monkeypatch):
    monkeypatch.setattr(ics, "MAX_ICS_BYTES", 100)
    respx.get("https://example.org/a.ics").mock(return_value=httpx.Response(200, text=SAMPLE))
    with pytest.raises(ValueError):
        await ics.download("https://example.org/a.ics")
