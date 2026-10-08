"""Germany's ten phenological seasons ("phänologische Jahreszeiten"), as used by the
Deutscher Wetterdienst: nature's calendar, read from what plants do.

Each season opens with an indicator plant (hazel flowering opens early spring, and so on).
The dates below are rounded long-term averages for Germany; a real year can be two weeks
early or late, and the south-west runs ahead of the north-east. Cultural colour, not a
measurement of this year.

Tuple: (month, day, name, indicator in German, en, fr)
"""

from __future__ import annotations

from datetime import date

SEASONS = (
    (2, 26, "Vorfrühling", "Die Hasel blüht", "Hazel in flower", "Le noisetier fleurit"),
    (3, 26, "Erstfrühling", "Die Forsythie blüht", "Forsythia in flower", "Le forsythia fleurit"),
    (4, 24, "Vollfrühling", "Die Apfelbäume blühen", "Apple trees in blossom", "Les pommiers fleurissent"),
    (5, 23, "Frühsommer", "Der Holunder blüht", "Elder in flower", "Le sureau fleurit"),
    (6, 22, "Hochsommer", "Die Linde blüht", "Lime trees in flower", "Le tilleul fleurit"),
    (7, 25, "Spätsommer", "Frühe Äpfel sind reif", "Early apples ripen", "Les premières pommes mûrissent"),
    (8, 25, "Frühherbst", "Holunderbeeren sind reif", "Elderberries ripen", "Les baies de sureau mûrissent"),
    (9, 20, "Vollherbst", "Eicheln fallen", "Acorns fall", "Les glands tombent"),
    (10, 15, "Spätherbst", "Die Eichen färben sich", "Oaks turn colour", "Les chênes se colorent"),
    (11, 8, "Winter", "Die Eichen sind kahl", "Oaks are bare", "Les chênes sont nus"),
)

_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")


def current(today: date) -> dict:
    key = (today.month, today.day)
    starts = [(m, d) for m, d, *_ in SEASONS]
    idx = max((i for i, s in enumerate(starts) if s <= key), default=len(SEASONS) - 1)
    nxt = (idx + 1) % len(SEASONS)
    n_month, n_day = starts[nxt]
    next_start = date(today.year, n_month, n_day)
    if next_start <= today:
        next_start = date(today.year + 1, n_month, n_day)
    _, _, name, de, en, fr = SEASONS[idx]
    return {
        "kind": "phenology",
        "number": idx + 1,
        "glyph": _ROMAN[idx],
        "seal": "◐",
        "title": {"de": name, "en": name, "fr": name},
        "sub": {"de": de, "en": en, "fr": fr},
        "note": {"de": "Phänologische Jahreszeit", "en": "Season of nature (DWD)", "fr": "Saison de la nature (DWD)"},
        "next_change": next_start.isoformat(),
        "days_left": (next_start - today).days,
    }
