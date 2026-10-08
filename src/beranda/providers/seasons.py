"""One seasonal block per theme, all with the same shape so the display stays generic.

japan     -> the 72 micro-seasons (七十二候)
indonesia -> pranata mangsa, the Javanese farmers' calendar
france    -> the French Republican calendar's day names
germany   -> the ten phenological seasons of the Deutscher Wetterdienst
spain, italy, portugal -> astronomical season + proverb of the month
brazil    -> astronomical season (southern hemisphere aware) + saying of the day
"""

from __future__ import annotations

from datetime import date

from . import almanac, microseasons, phenology, pranata, republican

THEMES = ("japan", "indonesia", "france", "germany", "spain", "italy", "portugal", "brazil")


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


def current(theme: str, today: date, tz: str = "Europe/Paris", latitude: float = 48.0) -> dict:
    if theme == "indonesia":
        return pranata.current(today)
    if theme == "france":
        return republican.current(today)
    if theme == "germany":
        return phenology.current(today)
    traditions = {"spain": "es", "italy": "it", "portugal": "pt", "brazil": "pt-BR"}
    if theme in traditions:
        return almanac.current(today, tz, latitude, traditions[theme])
    return _japan(today)
