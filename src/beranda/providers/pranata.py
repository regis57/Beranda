"""Pranata mangsa: the Javanese farmers' calendar of 12 seasons (mangsa).

Dates follow the commonly published solar scheme (it starts on 22 June). Kawolu lasts one
day longer in leap years. The tradition is Javanese and tuned to Java's monsoon; elsewhere
in Indonesia the seasons differ, so treat it as cultural colour, not a forecast.

Tuple: (month, day, name, javanese epithet, id, en, fr)
"""

from __future__ import annotations

from datetime import date

MANGSA = (
    (6, 22, "Kasa", "Sesotya murca ing embanan",
     "Daun berguguran, ranting mengering; saatnya panen palawija.",
     "Leaves fall and twigs dry out; time to harvest secondary crops.",
     "Les feuilles tombent et les branches sèchent ; récolte des cultures sèches."),
    (8, 2, "Karo", "Bantala rengka",
     "Tanah retak dan kering; mata air menyusut.",
     "The ground cracks in the dry; springs shrink.",
     "La terre se fend de sécheresse ; les sources diminuent."),
    (8, 25, "Katelu", "Suta manut ing bapa",
     "Umbi-umbian mulai merambat; angin kering bertiup.",
     "Tubers start to climb; dry winds blow.",
     "Les tubercules commencent à grimper ; vents secs."),
    (9, 18, "Kapat", "Waspa kumembeng jroning kalbu",
     "Mata air terisi lagi; pohon mangga mulai berbunga.",
     "Springs fill again; mango trees begin to flower.",
     "Les sources se remplissent ; les manguiers fleurissent."),
    (10, 13, "Kalima", "Pancuran emas sumawur ing jagad",
     "Hujan pertama turun; waktunya mulai menanam.",
     "The first rains fall; time to start planting.",
     "Premières pluies ; le temps des semis."),
    (11, 9, "Kanem", "Rasa mulya kasucian",
     "Buah-buahan masak: durian, rambutan, manggis.",
     "Fruit ripens: durian, rambutan, mangosteen.",
     "Les fruits mûrissent : durian, ramboutan, mangoustan."),
    (12, 22, "Kapitu", "Wisa kentar ing maruta",
     "Puncak hujan; banjir dan penyakit mengintai.",
     "Peak rains; floods and sickness lurk.",
     "Pic des pluies ; crues et maladies guettent."),
    (2, 3, "Kawolu", "Anjrah jroning kayun",
     "Padi menghijau; kucing dan hewan berahi.",
     "Rice turns green; animals mate.",
     "Le riz verdit ; les animaux s'accouplent."),
    (3, 1, "Kasanga", "Wedaring wacana mulya",
     "Padi berbunga; jangkrik dan tonggeret bersuara.",
     "Rice flowers; crickets and cicadas sing.",
     "Le riz fleurit ; grillons et cigales chantent."),
    (3, 26, "Kadasa", "Gedhong minep jroning pasarean",
     "Padi berisi; hewan mengandung dan bersarang.",
     "Rice fills out; animals nest and carry young.",
     "Le riz se remplit ; les animaux nichent."),
    (4, 19, "Dhesta", "Sotya sinarawedi",
     "Burung mengerami dan menyuapi anaknya.",
     "Birds hatch and feed their young.",
     "Les oiseaux couvent et nourrissent leurs petits."),
    (5, 12, "Saddha", "Tirta sah saking sasana",
     "Musim kemarau tiba; malam terasa dingin.",
     "The dry season arrives; nights turn cool.",
     "La saison sèche arrive ; les nuits fraîchissent."),
)

_ORDER = sorted(range(len(MANGSA)), key=lambda i: (MANGSA[i][0], MANGSA[i][1]))


def current(today: date) -> dict:
    key = (today.month, today.day)
    position = max(p for p, i in enumerate(_ORDER) if (MANGSA[_ORDER[p]][0], MANGSA[_ORDER[p]][1]) <= key) \
        if key >= (MANGSA[_ORDER[0]][0], MANGSA[_ORDER[0]][1]) else len(_ORDER) - 1
    idx = _ORDER[position]
    nxt = _ORDER[(position + 1) % len(_ORDER)]
    n_month, n_day = MANGSA[nxt][0], MANGSA[nxt][1]
    next_start = date(today.year, n_month, n_day)
    if next_start <= today:
        next_start = date(today.year + 1, n_month, n_day)
    _, _, name, epithet, id_, en, fr = MANGSA[idx]
    return {
        "kind": "mangsa",
        "number": idx + 1,
        "glyph": f"{idx + 1:02d}",
        "seal": "M",
        "title": {"id": f"Mangsa {name}", "en": f"Mangsa {name}", "fr": f"Mangsa {name}"},
        "sub": {"id": id_, "en": en, "fr": fr},
        "note": epithet,
        "next_change": next_start.isoformat(),
        "days_left": (next_start - today).days,
    }
