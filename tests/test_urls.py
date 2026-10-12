"""The one check every address Beranda downloads from has to pass."""

import pytest

from beranda.urls import checked_calendar_url, checked_url, checked_url_or_empty


@pytest.mark.parametrize("url", [
    "https://example.org/feed.xml",
    "http://192.168.1.50:8080/guide.xml.gz",  # a guide served by another box at home is fine
    "https://example.org/a.ics?export",
])
def test_plain_web_addresses_are_accepted(url):
    assert checked_url(url) == url


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",          # would read a file off the Pi instead of downloading
    "ftp://example.org/feed.xml",
    "https://user:secret@example.org/feed.xml",  # a password would end up in a log one day
    "https://",                    # no site name
    "not a url at all",
    "https://example.org/a\nb",    # an invisible character splits one address into two
    "",
])
def test_anything_else_is_refused(url):
    with pytest.raises(ValueError):
        checked_url(url)


def test_an_address_that_is_far_too_long_is_refused():
    with pytest.raises(ValueError):
        checked_url("https://example.org/" + "a" * 3000)


def test_an_empty_box_simply_turns_that_part_off():
    assert checked_url_or_empty("") == ""
    assert checked_url_or_empty("  ") == ""
    with pytest.raises(ValueError):
        checked_url_or_empty("file:///etc/passwd")


def test_calendar_links_may_be_webcal():
    """Calendars hand out webcal:// links; the reader swaps it for https before downloading."""
    assert checked_calendar_url("webcal://example.org/a.ics") == "webcal://example.org/a.ics"
    assert checked_calendar_url("WEBCALS://example.org/a.ics") == "WEBCALS://example.org/a.ics"
    with pytest.raises(ValueError):
        checked_calendar_url("webcal://")


def test_a_bad_calendar_link_is_caught_when_the_settings_are_saved():
    from beranda.config import from_dict
    with pytest.raises(ValueError):
        from_dict({"calendar": {"ics_urls": ["file:///etc/passwd"]}})
