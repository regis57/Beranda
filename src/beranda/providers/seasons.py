"""One seasonal block per theme, all with the same shape so the display stays generic.

japan     -> the 72 micro-seasons (七十二候)
indonesia -> pranata mangsa, the Javanese farmers' calendar
france    -> the French Republican calendar's day names
germany   -> the ten phenological seasons of the Deutscher Wetterdienst
spain, italy, portugal -> astronomical season + proverb of the month
brazil    -> astronomical season (southern hemisphere aware) + saying of the day
africa    -> a Swahili proverb (methali) for the day
arab      -> the Hijri date (Umm al-Qura), computed by the display with Intl
america   -> the traditional name of the next full moon
india     -> the season (ṛtu) and the lunar day (tithi)
china     -> the 24 solar terms (节气), plus the lunar date added by the display
oceania   -> the Tahitian seasons of the Pleiades (Matari'i)
creole    -> carême / hivernage (or the austral seasons) and a Haitian Creole proverb
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from . import (
    almanac,
    astro,
    creole,
    fullmoons,
    jieqi,
    matarii,
    methali,
    microseasons,
    phenology,
    pranata,
    republican,
    ritu,
)

THEMES = (
    "japan", "indonesia", "france", "germany", "spain", "italy", "portugal", "brazil",
    "africa", "arab", "america", "india", "china", "oceania", "creole",
)


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


def _hijri() -> dict:
    # Python has no Umm al-Qura calendar; every browser engine does (Intl), so the display fills
    # in the day, month and year. Countries that sight the moon can differ by a day.
    return {
        "kind": "hijri", "number": 0, "glyph": "", "seal": "۞", "title": {}, "sub": {},
        "note": {"en": "Hijri calendar (Umm al-Qura), ±1 day", "fr": "Calendrier hégirien (Umm al-Qura), ±1 jour",
                 "ar": "التقويم الهجري (أم القرى)، ± يوم"},
        "next_change": None, "days_left": None,
    }


def current(
    theme: str, today: date, tz: str = "Europe/Paris", latitude: float = 48.0,
    now: datetime | None = None,
) -> dict:
    if theme == "africa":
        return methali.current(today)
    if theme == "arab":
        return _hijri()
    if theme == "america":
        return fullmoons.current(today, tz)
    if theme == "india":
        moment = now or datetime.combine(today, time(12), ZoneInfo(tz))
        return ritu.current(today, astro.moon(moment, latitude)["phase"])
    if theme == "china":
        return jieqi.current(today)
    if theme == "oceania":
        return matarii.current(today)
    if theme == "creole":
        return creole.current(today, latitude)
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
