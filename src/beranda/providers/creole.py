"""Creole theme: the two tropical seasons, and a Haitian Creole proverb (pwovèb) each day.

North of the equator (Antilles, Haiti, Guiana) the year turns between the dry season,
"carême", and the rainy, cyclone season, "hivernage", which matches the official Atlantic
hurricane season (1 June – 30 November). South of it (Réunion, Mauritius, Seychelles)
the cyclone season of the south-west Indian Ocean runs from 15 November to 30 April.
"""

from __future__ import annotations

from datetime import date

# (Haitian Creole, French, English)
PWOVEB = (
    ("Piti piti zwazo fè nich li.", "Petit à petit, l'oiseau fait son nid.", "Little by little, the bird builds its nest."),
    ("Dèyè mòn gen mòn.", "Derrière les montagnes, il y a des montagnes.", "Beyond the mountains, more mountains."),
    ("Men anpil, chay pa lou.", "Avec beaucoup de mains, la charge n'est pas lourde.", "Many hands make the load light."),
    ("Sak vid pa kanpe.", "Un sac vide ne tient pas debout.", "An empty sack cannot stand up."),
    ("Chak jou pa dimanch.", "Tous les jours ne sont pas dimanche.", "Not every day is Sunday."),
    ("Kreyon Bondye pa gen gòm.", "Le crayon de Dieu n'a pas de gomme.", "God's pencil has no eraser."),
    ("Ravèt pa janm gen rezon devan poul.", "Le cafard n'a jamais raison devant la poule.", "The cockroach is never right before the hen."),
    ("Bèl dan pa di kè kontan.", "De belles dents ne disent pas un cœur content.", "A nice smile does not mean a happy heart."),
    ("Wòch nan dlo pa konnen doulè wòch nan solèy.", "La pierre dans l'eau ignore la peine de la pierre au soleil.", "The stone in the water knows nothing of the stone in the sun."),
    ("Tout moun se moun.", "Tout le monde est quelqu'un.", "Every person is a person."),
    ("Ti chen gen fòs devan kay mèt li.", "Le petit chien est fort devant la maison de son maître.", "A small dog is brave in front of its master's house."),
    ("Bourik travay, chwal galonnen.", "L'âne travaille, le cheval porte les galons.", "The donkey works, the horse gets the medals."),
)

NORTH = {
    "dry": ("Carême", "Sezon sèk", "Dry season (carême)", "Carême, la saison sèche"),
    "wet": ("Hivernage", "Sezon lapli", "Rainy season (hivernage)", "Hivernage, pluies et cyclones"),
}
SOUTH = {
    "dry": ("Hiver austral", "Sezon fre", "Cool dry season", "Hiver austral, saison sèche et fraîche"),
    "wet": ("Été austral", "Sezon siklòn", "Hot cyclone season", "Été austral, saison chaude des cyclones"),
}


def current(today: date, latitude: float) -> dict:
    if latitude >= 0:
        names = NORTH
        wet_start, dry_start = date(today.year, 6, 1), date(today.year, 12, 1)
    else:
        names = SOUTH
        dry_start, wet_start = date(today.year, 5, 1), date(today.year, 11, 15)
    starts = sorted([(wet_start, "wet"), (dry_start, "dry")])
    if today < starts[0][0]:
        season = starts[1][1]
        next_start = starts[0][0]
    elif today < starts[1][0]:
        season = starts[0][1]
        next_start = starts[1][0]
    else:
        season = starts[1][1]
        next_start = date(today.year + 1, starts[0][0].month, starts[0][0].day)
    _, ht_name, en_long, fr_long = names[season]
    ht, fr, en = PWOVEB[today.toordinal() % len(PWOVEB)]
    return {
        "kind": "creole",
        "number": 1 if season == "dry" else 2,
        "glyph": "",  # the theme draws a madras check here
        "seal": "☀" if season == "dry" else "☂",
        "title": {"en": en_long, "fr": fr_long, "ht": ht_name},
        "sub": {"en": ht},
        "sub_lang": "ht",
        "note": {"en": en, "fr": fr, "ht": "Pwovèb kreyòl"},
        "next_change": next_start.isoformat(),
        "days_left": (next_start - today).days,
    }
