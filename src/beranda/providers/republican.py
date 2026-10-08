"""The French Republican calendar (1793-1805), used here as a poetic day-name.

Every day of the year has a plant, animal or tool as its name ("jour du Raisin"), written by
Fabre d'Églantine. The year starts on the autumn equinox as seen from Paris (the rule of the
original decree); we compute that day with Meeus's mean-equinox polynomial, which is within
about half an hour: only an equinox falling within that margin of Paris midnight could be
off by one day.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

MONTHS = (
    "Vendémiaire", "Brumaire", "Frimaire", "Nivôse", "Pluviôse", "Ventôse",
    "Germinal", "Floréal", "Prairial", "Messidor", "Thermidor", "Fructidor",
)
MONTH_MEANING = (
    "vendanges", "brumes", "frimas", "neige", "pluie", "vent",
    "germination", "fleurs", "prairies", "moissons", "chaleur", "fruits",
)
DECADE = ("Primidi", "Duodi", "Tridi", "Quartidi", "Quintidi", "Sextidi", "Septidi",
          "Octidi", "Nonidi", "Décadi")
SANSCULOTTIDES = ("Jour de la Vertu", "Jour du Génie", "Jour du Travail",
                  "Jour de l'Opinion", "Jour des Récompenses", "Jour de la Révolution")

_NAMES = """
Raisin|Safran|Châtaigne|Colchique|Cheval|Balsamine|Carotte|Amarante|Panais|Cuve|Pomme de terre|Immortelle|Potiron|Réséda|Âne|Belle de nuit|Citrouille|Sarrasin|Tournesol|Pressoir|Chanvre|Pêche|Navet|Amaryllis|Bœuf|Aubergine|Piment|Tomate|Orge|Tonneau
Pomme|Céleri|Poire|Betterave|Oie|Héliotrope|Figue|Scorsonère|Alisier|Charrue|Salsifis|Mâcre|Topinambour|Endive|Dindon|Chervis|Cresson|Dentelaire|Grenade|Herse|Bacchante|Azerole|Garance|Orange|Faisan|Pistache|Macjonc|Coing|Cormier|Rouleau
Raiponce|Turneps|Chicorée|Nèfle|Cochon|Mâche|Chou-fleur|Miel|Genièvre|Pioche|Cire|Raifort|Cèdre|Sapin|Chevreuil|Ajonc|Cyprès|Lierre|Sabine|Hoyau|Érable à sucre|Bruyère|Roseau|Oseille|Grillon|Pignon|Liège|Truffe|Olive|Pelle
Tourbe|Houille|Bitume|Soufre|Chien|Lave|Terre végétale|Fumier|Salpêtre|Fléau|Granit|Argile|Ardoise|Grès|Lapin|Silex|Marne|Pierre à chaux|Marbre|Van|Pierre à plâtre|Sel|Fer|Cuivre|Chat|Étain|Plomb|Zinc|Mercure|Crible
Lauréole|Mousse|Fragon|Perce-neige|Taureau|Laurier-thym|Amadouvier|Mézéréon|Peuplier|Coignée|Ellébore|Brocoli|Laurier|Avelinier|Vache|Buis|Lichen|If|Pulmonaire|Serpette|Thlaspi|Thimelé|Chiendent|Traînasse|Lièvre|Guède|Noisetier|Cyclamen|Chélidoine|Traîneau
Tussilage|Cornouiller|Violier|Troène|Bouc|Asaret|Alaterne|Violette|Marceau|Bêche|Narcisse|Orme|Fumeterre|Vélar|Chèvre|Épinard|Doronic|Mouron|Cerfeuil|Cordeau|Mandragore|Persil|Cochléaria|Pâquerette|Thon|Pissenlit|Sylvie|Capillaire|Frêne|Plantoir
Primevère|Platane|Asperge|Tulipe|Poule|Bette|Bouleau|Jonquille|Aulne|Couvoir|Pervenche|Charme|Morille|Hêtre|Abeille|Laitue|Mélèze|Ciguë|Radis|Ruche|Gainier|Romaine|Marronnier|Roquette|Pigeon|Lilas|Anémone|Pensée|Myrtille|Greffoir
Rose|Chêne|Fougère|Aubépine|Rossignol|Ancolie|Muguet|Champignon|Hyacinthe|Râteau|Rhubarbe|Sainfoin|Bâton-d'or|Chamérisier|Ver à soie|Consoude|Pimprenelle|Corbeille d'or|Arroche|Sarcloir|Statice|Fritillaire|Bourrache|Valériane|Carpe|Fusain|Civette|Buglosse|Sénevé|Houlette
Luzerne|Hémérocalle|Trèfle|Angélique|Canard|Mélisse|Fromental|Martagon|Serpolet|Faux|Fraise|Bétoine|Pois|Acacia|Caille|Œillet|Sureau|Pavot|Tilleul|Fourche|Barbeau|Camomille|Chèvrefeuille|Caille-lait|Tanche|Jasmin|Verveine|Thym|Pivoine|Chariot
Seigle|Avoine|Oignon|Véronique|Mulet|Romarin|Concombre|Échalote|Absinthe|Faucille|Coriandre|Artichaut|Girofle|Lavande|Chamois|Tabac|Groseille|Gesse|Cerise|Parc|Menthe|Cumin|Haricot|Orcanète|Pintade|Sauge|Ail|Vesce|Blé|Chalémie
Épeautre|Bouillon-blanc|Melon|Ivraie|Bélier|Prêle|Armoise|Carthame|Mûre|Arrosoir|Panic|Salicorne|Abricot|Basilic|Brebis|Guimauve|Lin|Amande|Gentiane|Écluse|Carline|Câprier|Lentille|Aunée|Loutre|Myrte|Colza|Lupin|Coton|Moulin
Prune|Millet|Lycoperdon|Escourgeon|Saumon|Tubéreuse|Sucrion|Apocyn|Réglisse|Échelle|Pastèque|Fenouil|Épine-vinette|Noix|Truite|Citron|Cardère|Nerprun|Tagète|Hotte|Églantier|Noisette|Houblon|Sorgho|Écrevisse|Bigarade|Verge d'or|Maïs|Marron|Panier
"""
DAY_NAMES = tuple(tuple(line.split("|")) for line in _NAMES.strip().splitlines())


def autumn_equinox(year: int) -> date:
    """The calendar day, in Paris, of the September equinox (Meeus ch. 27, mean value)."""
    y = (year - 2000) / 1000
    jde = 2451810.21715 + 365242.01767 * y - 0.11575 * y**2 + 0.00337 * y**3 + 0.00078 * y**4
    # JDE 2451545.0 is 2000-01-01 12:00 TT; TT is about 69 s ahead of UTC.
    utc = datetime(2000, 1, 1, 12, tzinfo=UTC) + timedelta(days=jde - 2451545.0, seconds=-69)
    return utc.astimezone(ZoneInfo("Europe/Paris")).date()


def current(today: date) -> dict:
    start = autumn_equinox(today.year)
    if today < start:
        start = autumn_equinox(today.year - 1)
    year_number = start.year - 1791
    ordinal = (today - start).days  # 0-based, 0..365
    if ordinal < 360:
        month, day = divmod(ordinal, 30)
        title = f"{day + 1} {MONTHS[month]}"
        sub = DAY_NAMES[month][day]
        note = f"{DECADE[day % 10]} · An {_roman(year_number)}"
        days_left = None
    else:
        extra = ordinal - 360
        title = f"{extra + 1} Sansculottides"
        sub = SANSCULOTTIDES[extra]
        note = f"An {_roman(year_number)}"
        days_left = None
    return {
        "kind": "republican",
        "number": ordinal + 1,
        "glyph": title.split()[0].zfill(2),
        "seal": "R",
        "title": {"fr": title, "en": title, "id": title},
        "sub": {"fr": sub, "en": sub, "id": sub},
        "note": note,
        "next_change": (today + timedelta(days=1)).isoformat(),
        "days_left": days_left,
    }


def _roman(n: int) -> str:
    out = ""
    for value, sym in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                       (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += sym
            n -= value
    return out
