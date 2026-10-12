"""One place that decides whether a web address Beranda was given is safe to download from.

Every address Beranda fetches - a news feed, a calendar link, a TV guide - is typed in by
the owner of the mirror on the settings page, and that page only answers on the home
network. Even so, each address is checked twice: once when the settings are saved, so a
typing mistake is caught while the person is still looking at the screen, and once again
just before the download, so an address put straight into the file by hand can never send
Beranda somewhere it should not go.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

MAX_LENGTH = 2000  # longer than any real feed address; a sign that something went wrong
_BAD_CHARACTER = re.compile(r"[\x00-\x20\x7f]")  # spaces, tabs, newlines, invisible characters


def checked_url(value: object, what: str = "address") -> str:
    """Return the address unchanged when it is a plain http:// or https:// link.

    Anything else raises `ValueError` with a sentence a person can act on. The checks are
    deliberately simple and explain themselves:
      * it must be http:// or https:// - no file://, no ftp://, nothing that could read a
        file off the Pi instead of downloading a page;
      * it must have a site name;
      * it must not hide a user name or a password in front of the site name, because that
        would end up in a log one day;
      * no invisible characters, which is how a single address gets turned into two.
    """
    url = str(value or "").strip()
    if not url:
        raise ValueError(f"the {what} is empty")
    if len(url) > MAX_LENGTH:
        raise ValueError(f"the {what} is far too long ({len(url)} characters)")
    if _BAD_CHARACTER.search(url):
        raise ValueError(f"the {what} contains a character that does not belong in a web address")
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError(f"the {what} must start with http:// or https://, got {url[:60]!r}")
    if not parts.hostname:
        raise ValueError(f"the {what} does not say which site to read")
    if parts.username or parts.password:
        raise ValueError(f"the {what} must not carry a user name or a password")
    return url


def checked_url_or_empty(value: object, what: str = "address") -> str:
    """Same as `checked_url`, but an empty box is fine: it simply turns that part off."""
    url = str(value or "").strip()
    return checked_url(url, what) if url else ""


def checked_calendar_url(value: object) -> str:
    """Same as `checked_url`, and also accepts the `webcal://` links calendars hand out.

    A `webcal://` address is an https address wearing a different hat; the calendar reader
    swaps it for https just before downloading, so it only has to pass the check here.
    """
    url = str(value or "").strip()
    probe = url
    for disguise in ("webcal://", "webcals://"):
        if probe.lower().startswith(disguise):
            probe = "https://" + probe[len(disguise):]
            break
    checked_url(probe, "calendar address")
    return url
