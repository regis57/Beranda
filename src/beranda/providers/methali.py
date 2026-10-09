"""African theme: a Swahili proverb (methali) for every day, with its meaning.

Swahili is spoken by well over a hundred million people across East and Central Africa;
these sayings are traditional and public domain.
"""

from __future__ import annotations

from datetime import date

# (Swahili, English, French)
METHALI = (
    ("Haba na haba hujaza kibaba.", "Little by little fills the measure.", "Petit à petit, on remplit la mesure."),
    ("Haraka haraka haina baraka.", "Hurry, hurry has no blessing.", "La précipitation n'apporte pas de bénédiction."),
    ("Umoja ni nguvu, utengano ni udhaifu.", "Unity is strength, division is weakness.", "L'union fait la force, la division la faiblesse."),
    ("Penye nia pana njia.", "Where there is a will, there is a way.", "Là où il y a une volonté, il y a un chemin."),
    ("Usipoziba ufa utajenga ukuta.", "Fill the crack, or you will rebuild the wall.", "Qui ne bouche pas la fissure rebâtira le mur."),
    ("Asiyesikia la mkuu huvunjika guu.", "Who will not heed the elders breaks a leg.", "Qui n'écoute pas les anciens se casse la jambe."),
    ("Mgeni njoo, mwenyeji apone.", "Let the guest come, so the host may prosper.", "Que l'invité vienne, et l'hôte prospère."),
    ("Kidole kimoja hakivunji chawa.", "One finger cannot crush a louse.", "Un seul doigt n'écrase pas un pou."),
    ("Maji yakimwagika hayazoleki.", "Spilt water cannot be gathered up.", "L'eau renversée ne se ramasse pas."),
    ("Dalili ya mvua ni mawingu.", "Clouds are the sign of rain.", "Les nuages annoncent la pluie."),
    ("Bandu bandu huisha gogo.", "Chip by chip, the log is used up.", "Copeau après copeau, la bûche disparaît."),
    ("Akili ni nywele, kila mtu ana zake.", "Wisdom is like hair: everyone has their own.", "La sagesse est comme les cheveux : chacun a les siens."),
    ("Mtaka cha mvunguni sharti ainame.", "Who wants what is under the bed must bend down.", "Qui veut ce qui est sous le lit doit se baisser."),
    ("Pole pole ndio mwendo.", "Slowly, slowly is the way to go.", "Doucement, c'est ainsi qu'on avance."),
    ("Mwenda pole hajikwai.", "Who walks slowly does not stumble.", "Qui marche doucement ne trébuche pas."),
    ("Fimbo ya mbali haiui nyoka.", "A distant stick does not kill the snake.", "Le bâton lointain ne tue pas le serpent."),
    ("Ukiona vyaelea, vimeundwa.", "What floats was built by someone.", "Ce qui flotte, quelqu'un l'a construit."),
    ("Mchumia juani hulia kivulini.", "Who toils in the sun eats in the shade.", "Qui peine au soleil mange à l'ombre."),
)


def current(today: date) -> dict:
    sw, en, fr = METHALI[today.toordinal() % len(METHALI)]
    return {
        "kind": "methali",
        "number": today.toordinal() % len(METHALI) + 1,
        "glyph": "",  # the theme draws a kente band here
        "seal": "✦",
        "title": {"en": sw},
        "title_lang": "sw",
        "sub": {"en": en, "fr": fr},  # Swahili readers see the English meaning
        "note": {"en": "Swahili proverb of the day", "fr": "Proverbe swahili du jour", "sw": "Methali ya leo"},
        "next_change": None,
        "days_left": None,
    }
