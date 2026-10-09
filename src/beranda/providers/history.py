""""On this day": what happened on today's date in history, from Wikipedia.

Wikipedia keeps a free, public "On this day" feed (no account, no key). We ask it one small
question a day - "what happened on this month and day?" - in the language of the person's
Wikipedia edition. That is also how the box stays about *their* part of the world: the French
Wikipedia talks mostly about France and the French-speaking world, the German one about
Germany, and so on. Nothing about the person is sent except the date and a language code.

Editorial "selected" events come first (the ones Wikipedia's own editors highlight), then
the general list. Not every language has such a feed; English is the fallback.
"""

from __future__ import annotations

import httpx

FEED_URL = "https://api.wikimedia.org/feed/v1/wikipedia/{lang}/onthisday/all/{month:02d}/{day:02d}"
USER_AGENT = "Beranda/0.12 (+https://github.com/regis57/Beranda) one small request a day"
MAX_EVENTS = 6
MAX_TEXT = 220  # characters: the box on the screen is small


async def _feed(language: str, month: int, day: int) -> dict:
    url = FEED_URL.format(lang=language, month=month, day=day)
    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(url)
        response.raise_for_status()
    return response.json()


def _clean(items: list, seen: set[str]) -> list[dict]:
    out: list[dict] = []
    for item in items or []:
        text = " ".join(str(item.get("text") or "").split())
        year = item.get("year")
        if not text or not isinstance(year, int) or text in seen:
            continue
        seen.add(text)
        if len(text) > MAX_TEXT:
            text = text[: MAX_TEXT - 1].rstrip() + "…"
        out.append({"year": year, "text": text})
    return out


def parse(feed: dict, limit: int = MAX_EVENTS) -> list[dict]:
    """The feed's events as [{"year": 1920, "text": "..."}]: highlights first, no duplicates,
    then the rest with the most recent history first."""
    seen: set[str] = set()
    selected = _clean(feed.get("selected"), seen)
    rest = _clean(feed.get("events"), seen)
    rest.sort(key=lambda e: -e["year"])
    return (selected + rest)[:limit]


async def fetch(language: str, month: int, day: int) -> list[dict]:
    """Today's events in `language` (e.g. "fr", "pt-BR" -> "pt"), or English if that edition
    has no such feed."""
    base = (language or "en").split("-")[0].lower()
    for lang in dict.fromkeys([base, "en"]):
        try:
            events = parse(await _feed(lang, month, day))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404) and lang != "en":
                continue  # this language has no "On this day" feed: try English
            raise
        if events:
            return events
    return []
