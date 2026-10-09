"""Oceanian theme: the two seasons of the Tahitian year, set by the Pleiades (Matari'i).

When the Pleiades rise at dusk (Matari'i i ni'a, around 20 November) the season of
abundance (tau 'auhune) begins; when they disappear at dusk (Matari'i i raro, around
20 May) the cooler, leaner season (tau o'e) begins. Both dates are celebrated in
French Polynesia; the exact sighting varies by a few days.
"""

from __future__ import annotations

from datetime import date

ABUNDANCE = ("Matari'i i ni'a", "Tau 'auhune",
             "Season of abundance", "Saison de l'abondance")
LEAN = ("Matari'i i raro", "Tau o'e",
        "Cool, leaner season", "Saison fraîche, de la disette")


def current(today: date) -> dict:
    up = date(today.year, 11, 20)
    down = date(today.year, 5, 20)
    if down <= today < up:
        season, next_start = LEAN, up
    else:
        season = ABUNDANCE
        next_start = down if today < down else date(today.year + 1, 5, 20)
    star, tau, en, fr = season
    return {
        "kind": "matarii",
        "number": 1 if season is ABUNDANCE else 2,
        "glyph": "",  # the theme draws the seven stars of the Pleiades
        "seal": "✶",
        "title": {"en": star},
        "title_lang": "ty",
        "sub": {"en": f"{tau} · {en}", "fr": f"{tau} · {fr}"},
        "note": {"en": "Tahitian calendar of the Pleiades", "fr": "Calendrier tahitien des Pléiades"},
        "next_change": next_start.isoformat(),
        "days_left": (next_start - today).days,
    }
