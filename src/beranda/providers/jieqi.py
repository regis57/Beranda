"""Chinese theme: the 24 solar terms (二十四节气).

A solar term begins each time the Sun's apparent longitude passes a multiple of 15°
(0° is the spring equinox). We compute that longitude with Meeus's low-precision solar
formula (ch. 25), good to about a hundredth of a degree: a quarter of an hour of time.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

# index = floor(longitude / 15°); (hanzi, pinyin, English, French)
TERMS = (
    ("春分", "chūnfēn", "Spring Equinox", "Équinoxe de printemps"),
    ("清明", "qīngmíng", "Clear and Bright", "Clarté pure"),
    ("谷雨", "gǔyǔ", "Grain Rain", "Pluie des céréales"),
    ("立夏", "lìxià", "Start of Summer", "Début de l'été"),
    ("小满", "xiǎomǎn", "Grain Buds", "Petite abondance"),
    ("芒种", "mángzhòng", "Grain in Ear", "Épis barbus"),
    ("夏至", "xiàzhì", "Summer Solstice", "Solstice d'été"),
    ("小暑", "xiǎoshǔ", "Minor Heat", "Petite chaleur"),
    ("大暑", "dàshǔ", "Major Heat", "Grande chaleur"),
    ("立秋", "lìqiū", "Start of Autumn", "Début de l'automne"),
    ("处暑", "chǔshǔ", "End of Heat", "Fin de la chaleur"),
    ("白露", "báilù", "White Dew", "Rosée blanche"),
    ("秋分", "qiūfēn", "Autumn Equinox", "Équinoxe d'automne"),
    ("寒露", "hánlù", "Cold Dew", "Rosée froide"),
    ("霜降", "shuāngjiàng", "Frost's Descent", "Descente du givre"),
    ("立冬", "lìdōng", "Start of Winter", "Début de l'hiver"),
    ("小雪", "xiǎoxuě", "Minor Snow", "Petite neige"),
    ("大雪", "dàxuě", "Major Snow", "Grande neige"),
    ("冬至", "dōngzhì", "Winter Solstice", "Solstice d'hiver"),
    ("小寒", "xiǎohán", "Minor Cold", "Petit froid"),
    ("大寒", "dàhán", "Major Cold", "Grand froid"),
    ("立春", "lìchūn", "Start of Spring", "Début du printemps"),
    ("雨水", "yǔshuǐ", "Rain Water", "Eau de pluie"),
    ("惊蛰", "jīngzhé", "Awakening of Insects", "Réveil des insectes"),
)


def sun_longitude(when: datetime) -> float:
    """Apparent ecliptic longitude of the Sun, degrees."""
    jd = when.astimezone(UTC).timestamp() / 86400 + 2440587.5
    t = (jd - 2451545.0) / 36525
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m) + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * t)
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega)) % 360


def _index_on(day: date, tz: str) -> int:
    end_of_day = datetime(day.year, day.month, day.day, 23, 59, tzinfo=ZoneInfo(tz))
    return int(sun_longitude(end_of_day) // 15)


def current(today: date, tz: str = "Asia/Shanghai") -> dict:
    """The term in force at the end of `today` in `tz` (China uses Beijing time)."""
    idx = _index_on(today, tz)
    day = today
    while _index_on(day, tz) == idx:
        day += timedelta(days=1)
    hanzi, pinyin, en, fr = TERMS[idx]
    rank = (idx - 21) % 24 + 1  # counted from 立春, the first term of the year
    return {
        "kind": "jieqi",
        "number": idx + 1,
        "glyph": hanzi,
        "seal": "节",
        "title": {"en": en, "fr": fr, "zh": f"二十四节气 · 第{rank}", "zh-TW": f"二十四節氣 · 第{rank}"},
        "sub": {"en": pinyin},
        "note": None,  # the display adds today's Chinese lunar date
        "next_change": day.isoformat(),
        "days_left": (day - today).days,
    }
