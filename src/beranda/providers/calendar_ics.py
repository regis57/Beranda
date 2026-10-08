"""Read-only calendars over ICS URLs.

Google ("secret address in iCal format"), Apple iCloud (public calendar link), Outlook,
Nextcloud, Proton... all hand out an .ics URL. One parser covers them all: no OAuth,
no Google Cloud project, nothing to configure but a link.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import recurring_ical_events
from icalendar import Calendar

USER_AGENT = "Beranda/0.2 (+https://github.com/regis57/Beranda)"
MAX_ICS_BYTES = 8 * 1024 * 1024  # a Pi 3B should not be fed a 200 MB calendar


def normalise_url(url: str) -> str:
    """`webcal://` is just https in disguise."""
    if url.lower().startswith("webcal://"):
        return "https://" + url[len("webcal://") :]
    return url


async def download(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=15, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        response = await client.get(normalise_url(url))
        response.raise_for_status()
        if len(response.content) > MAX_ICS_BYTES:
            raise ValueError("calendar file is too large")
        return response.text


def _as_local(value: date | datetime, zone: ZoneInfo) -> tuple[datetime, bool]:
    """Return (aware datetime in `zone`, is_all_day)."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=zone), False
        return value.astimezone(zone), False
    return datetime.combine(value, time.min, tzinfo=zone), True


def events_from_ics(text: str, start: date, end: date, tz: str, source: int = 0) -> list[dict]:
    """Events overlapping [start, end] (inclusive), recurring ones expanded."""
    zone = ZoneInfo(tz)
    calendar = Calendar.from_ical(text)
    window_end = end + timedelta(days=1)
    out: list[dict] = []

    for component in recurring_ical_events.of(calendar).between(start, window_end):
        begin, all_day = _as_local(component.start, zone)
        finish_raw = component.end
        finish, _ = _as_local(finish_raw, zone)
        title = str(component.get("SUMMARY", "")).strip() or "—"
        out.append(
            {
                "title": title,
                "start": begin.isoformat(),
                "end": finish.isoformat(),
                "all_day": all_day,
                "calendar": source,
            }
        )

    out.sort(key=lambda e: (e["start"], e["title"]))
    return out
