"""Indian theme: the six seasons (ṛtu) of the Indian year, and the lunar day (tithi).

The ṛtu follow the classical two-month pattern, given here in their usual modern
approximation on the Gregorian calendar. The tithi is the lunar day: the Moon gains 12°
on the Sun for each one, 15 in the bright half (śukla pakṣa) up to the full moon, 15 in the
dark half (kṛṣṇa pakṣa) down to the new moon. Computed from the real Moon-Sun elongation,
it changes within a few minutes of the almanac (pañcāṅga) of your temple.
"""

from __future__ import annotations

from datetime import date, datetime

from beranda.providers import astro, jieqi

# (start month, start day, Devanagari, transliteration, English, French)
RITU = (
    (1, 15, "शिशिर", "Śiśira", "late winter", "fin de l'hiver"),
    (3, 15, "वसंत", "Vasanta", "spring", "printemps"),
    (5, 15, "ग्रीष्म", "Grīṣma", "summer", "été"),
    (7, 15, "वर्षा", "Varṣā", "monsoon", "mousson"),
    (9, 15, "शरद", "Śarad", "autumn", "automne"),
    (11, 15, "हेमंत", "Hemanta", "early winter", "début de l'hiver"),
)
TITHI = (
    ("प्रतिपदा", "Pratipadā"), ("द्वितीया", "Dvitīyā"), ("तृतीया", "Tṛtīyā"), ("चतुर्थी", "Caturthī"),
    ("पंचमी", "Pañcamī"), ("षष्ठी", "Ṣaṣṭhī"), ("सप्तमी", "Saptamī"), ("अष्टमी", "Aṣṭamī"),
    ("नवमी", "Navamī"), ("दशमी", "Daśamī"), ("एकादशी", "Ekādaśī"), ("द्वादशी", "Dvādaśī"),
    ("त्रयोदशी", "Trayodaśī"), ("चतुर्दशी", "Caturdaśī"),
)
FULL = ("पूर्णिमा", "Pūrṇimā")
NEW = ("अमावस्या", "Amāvasyā")


def tithi(phase: float) -> tuple[str, str]:
    """phase: 0 = new moon, 0.5 = full moon (as in astro.moon)."""
    index = int(phase * 30) % 30  # 0..29
    bright = index < 15
    n = index % 15
    if n == 14:
        dev, latin = FULL if bright else NEW
    else:
        dev, latin = TITHI[n]
    paksha_dev, paksha = ("शुक्ल", "Śukla") if bright else ("कृष्ण", "Kṛṣṇa")
    return f"{paksha_dev} {dev}", f"{paksha} {latin}"


def elongation_fraction(when: datetime) -> float:
    """How far the Moon has run ahead of the Sun, as a fraction of a full turn (0 = new moon)."""
    return ((astro.moon_longitude(when) - jieqi.sun_longitude(when)) % 360) / 360


def current(today: date, phase: float | datetime) -> dict:
    """phase: the moment itself (preferred), or a phase fraction as in astro.moon.

    A tithi is defined by elongation, not by time: the Moon runs faster near perigee, so the
    even, time-based phase of astro.moon can be a whole tithi off for up to 17 hours. Given
    the moment, the true elongation is used instead.
    """
    if isinstance(phase, datetime):
        phase = elongation_fraction(phase)
    key = (today.month, today.day)
    idx = max((i for i, r in enumerate(RITU) if (r[0], r[1]) <= key), default=len(RITU) - 1)
    nxt = RITU[(idx + 1) % len(RITU)]
    next_start = date(today.year + (1 if (nxt[0], nxt[1]) <= key else 0), nxt[0], nxt[1])
    _, _, dev, latin, en, fr = RITU[idx]
    t_dev, t_latin = tithi(phase)
    return {
        "kind": "ritu",
        "number": idx + 1,
        "glyph": dev,
        "seal": "ऋ",
        "title": {"en": f"{latin} · {en}", "fr": f"{latin} · {fr}", "hi": f"{dev} ऋतु"},
        "sub": {"en": f"{t_dev} · {t_latin}"},
        "note": {"en": "Season (ṛtu) and lunar day (tithi)", "fr": "Saison (ṛtu) et jour lunaire (tithi)",
                 "hi": "ऋतु और तिथि"},
        "next_change": next_start.isoformat(),
        "days_left": (next_start - today).days,
    }
