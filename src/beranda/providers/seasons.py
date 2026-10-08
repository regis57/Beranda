"""One seasonal calendar per theme, all with the same shape so the display stays generic.

japan     -> the 72 micro-seasons (七十二候)
indonesia -> pranata mangsa, the Javanese farmers' calendar
france    -> the French Republican calendar's day names
"""

from __future__ import annotations

from datetime import date

from . import microseasons, pranata, republican


def _japan(today: date) -> dict:
    ko = microseasons.current(today)
    return {
        **ko,
        "kind": "ko",
        "glyph": ko["kanji"],
        "seal": "候",
        "title": {"en": ko["en"], "fr": ko["fr"]},
        "sub": {"en": ko["romaji"]},
        "note": None,
    }


CALENDARS = {"japan": _japan, "indonesia": pranata.current, "france": republican.current}


def current(theme: str, today: date) -> dict:
    return CALENDARS.get(theme, _japan)(today)
