"""Offline demo data, used for screenshots and for trying Beranda without any setup.

Everything that depends on the date (moon, sunrise, micro-season, public holidays) is
real; only the weather and the agenda below are invented. The display says "demo" so
nobody mistakes it for a forecast.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from ..config import KeyDate

# A believable week of autumn weather: (WMO code, tmax, tmin, rain mm, rain probability %)
_WEEK = (
    (3, 14, 8, 0.4, 35),
    (61, 13, 9, 4.2, 80),
    (80, 12, 8, 2.1, 65),
    (3, 12, 7, 0.0, 15),
    (1, 15, 6, 0.0, 5),
    (0, 17, 7, 0.0, 0),
    (2, 16, 9, 0.3, 25),
)


def weather(today: date, now: datetime, units: str = "metric") -> dict:
    def conv(c: int) -> int:
        return round(c * 9 / 5 + 32) if units == "imperial" else c

    days = []
    for i, (code, tmax, tmin, rain, pop) in enumerate(_WEEK):
        day = today + timedelta(days=i)
        days.append(
            {
                "date": day.isoformat(),
                "code": code,
                "tmax": conv(tmax),
                "tmin": conv(tmin),
                "precip": rain,
                "pop": pop,
                "sunrise": f"{day.isoformat()}T07:52",
                "sunset": f"{day.isoformat()}T18:55",
                "uv": 2.0,
            }
        )
    return {
        "current": {
            "time": now.replace(second=0, microsecond=0).isoformat(timespec="minutes"),
            "temp": conv(11),
            "feels": conv(9),
            "humidity": 78,
            "wind": 14 if units != "imperial" else 9,
            "wind_dir": 225,
            "code": 3,
            "is_day": 7 <= now.hour < 19,
            "precip": 0.0,
        },
        # light rain arriving in about 45 minutes, heaviest around an hour from now
        "rain": {
            "intervals": [0.0, 0.0, 0.0, 0.2, 0.5, 0.9, 0.6, 0.3],
            "raining_now": False,
            "starts_in_min": 45,
            "stops_in_min": None,
        },
        "daily": days,
        "units": (
            {"temp": "°F", "wind": "mph", "precip": "in"}
            if units == "imperial"
            else {"temp": "°C", "wind": "km/h", "precip": "mm"}
        ),
        "fetched_at": now.isoformat(timespec="seconds"),
        "source": "demo",
    }


# Invented agenda, in the display language: (yoga, dentist, dinner, market, weekend,
# birthday, remembrance, wedding anniversary).
_AGENDA = {
    "en": ("Yoga", "Dentist", "Dinner at Sam's", "Market", "Weekend away", "Léa", "Grandpa", "Wedding anniversary"),
    "fr": ("Yoga", "Dentiste", "Dîner chez Sam", "Marché", "Week-end en Alsace", "Léa", "Papi", "Anniversaire de mariage"),
    "de": ("Yoga", "Zahnarzt", "Abendessen bei Sam", "Wochenmarkt", "Wochenende an der Ostsee", "Lea", "Opa", "Hochzeitstag"),
    "es": ("Yoga", "Dentista", "Cena en casa de Sam", "Mercado", "Fin de semana en la sierra", "Lea", "Abuelo", "Aniversario de boda"),
    "it": ("Yoga", "Dentista", "Cena da Sam", "Mercato", "Weekend al lago", "Lea", "Nonno", "Anniversario di matrimonio"),
    "pt": ("Ioga", "Dentista", "Jantar em casa do Sam", "Mercado", "Fim de semana no Alentejo", "Lea", "Avô", "Aniversário de casamento"),
    "pt-BR": ("Ioga", "Dentista", "Jantar na casa do Sam", "Feira", "Fim de semana na praia", "Lea", "Vovô", "Aniversário de casamento"),
    "id": ("Yoga", "Dokter gigi", "Makan malam di rumah Sam", "Pasar", "Akhir pekan ke Bandung", "Ayu", "Kakek", "Ulang tahun pernikahan"),
    "ja": ("ヨガ", "歯医者", "サムの家で夕食", "朝市", "週末旅行", "結衣", "祖父", "結婚記念日"),
    "ar": ("يوغا", "طبيب الأسنان", "عشاء عند سامي", "السوق", "عطلة نهاية الأسبوع", "ليلى", "الجد", "ذكرى الزواج"),
    "sw": ("Yoga", "Daktari wa meno", "Chakula cha jioni kwa Sam", "Soko", "Wikendi Mombasa", "Amani", "Babu", "Maadhimisho ya ndoa"),
    "am": ("ዮጋ", "የጥርስ ሐኪም", "ራት ከሳም ጋር", "ገበያ", "የሳምንት መጨረሻ ጉዞ", "ሊያ", "አያት", "የጋብቻ በዓል"),
    "af": ("Joga", "Tandarts", "Ete by Sam", "Mark", "Naweek weg", "Lea", "Oupa", "Huweliksherdenking"),
}


def _agenda(language: str) -> tuple[str, ...]:
    return _AGENDA.get(language) or _AGENDA.get(language.split("-")[0]) or _AGENDA["en"]


def events(today: date, tz_offset_iso: str, language: str = "fr") -> list[dict]:
    """A few invented agenda entries relative to today. `tz_offset_iso` like '+02:00'."""
    yoga, dentist, dinner, market, weekend, *_ = _agenda(language)

    def at(offset_days: int, hh: int, mm: int = 0) -> str:
        d = today + timedelta(days=offset_days)
        return f"{d.isoformat()}T{hh:02d}:{mm:02d}:00{tz_offset_iso}"

    return [
        {"title": yoga, "start": at(0, 18, 30), "end": at(0, 19, 30), "all_day": False, "calendar": 0},
        {"title": dentist, "start": at(1, 9, 15), "end": at(1, 10), "all_day": False, "calendar": 0},
        {"title": dinner, "start": at(3, 20), "end": at(3, 22, 30), "all_day": False, "calendar": 0},
        {"title": market, "start": at(4, 8), "end": at(4, 12), "all_day": False, "calendar": 0},
        {
            "title": weekend,
            "start": f"{(today + timedelta(days=5)).isoformat()}T00:00:00{tz_offset_iso}",
            "end": f"{(today + timedelta(days=7)).isoformat()}T00:00:00{tz_offset_iso}",
            "all_day": True,
            "calendar": 0,
        },
    ]


def key_dates(today: date, language: str = "fr") -> tuple[KeyDate, ...]:
    """Invented personal dates falling inside the next few weeks."""
    *_, child, grandpa, wedding = _agenda(language)
    a = today + timedelta(days=3)
    b = today + timedelta(days=11)
    c = today + timedelta(days=17)
    return (
        KeyDate(a.month, a.day, child, "birth", a.year - 8),
        KeyDate(b.month, b.day, grandpa, "death", b.year - 12),
        KeyDate(c.month, c.day, wedding, "anniversary", c.year - 6),
    )


# Invented headlines, clearly fake on purpose (the display shows a "demo" badge too).
_HEADLINES = {
    "en": ("The town library extends its opening hours", "Cycle lanes: the new route opens on Monday",
           "Autumn fair: record attendance this weekend", "Night trains are back on the regional line"),
    "fr": ("La médiathèque élargit ses horaires d'ouverture", "Pistes cyclables : le nouveau tracé ouvre lundi",
           "Foire d'automne : affluence record ce week-end", "Le train de nuit revient sur la ligne régionale"),
    "de": ("Die Stadtbibliothek verlängert ihre Öffnungszeiten", "Radweg: die neue Strecke öffnet am Montag",
           "Herbstmarkt: Besucherrekord am Wochenende", "Nachtzüge fahren wieder auf der Regionallinie"),
    "es": ("La biblioteca municipal amplía su horario", "Carril bici: el nuevo trazado abre el lunes",
           "Feria de otoño: récord de visitantes este fin de semana", "Vuelven los trenes nocturnos a la línea regional"),
    "it": ("La biblioteca comunale allunga gli orari", "Pista ciclabile: il nuovo tratto apre lunedì",
           "Fiera d'autunno: record di visitatori nel fine settimana", "Tornano i treni notturni sulla linea regionale"),
    "pt": ("A biblioteca municipal alarga o horário", "Ciclovia: o novo troço abre na segunda-feira",
           "Feira de outono: afluência recorde no fim de semana", "Os comboios noturnos voltam à linha regional"),
    "pt-BR": ("Biblioteca municipal amplia o horário de funcionamento", "Ciclovia: novo trecho abre na segunda-feira",
              "Feira de primavera bate recorde de público", "Trem noturno volta à linha regional"),
    "id": ("Perpustakaan kota memperpanjang jam buka", "Jalur sepeda baru dibuka hari Senin",
           "Pasar malam akhir pekan pecahkan rekor pengunjung", "Kereta malam kembali beroperasi di jalur regional"),
    "ja": ("市立図書館、開館時間を延長", "新しい自転車道、月曜に開通", "秋祭り、週末に来場者数が過去最多", "地域線に夜行列車が復活"),
    "ar": ("مكتبة المدينة تمدد ساعات العمل", "افتتاح مسار الدراجات الجديد يوم الاثنين",
           "معرض الخريف يسجل رقما قياسيا في عدد الزوار", "عودة قطار الليل إلى الخط الإقليمي"),
    "am": ("የከተማው ቤተ መጻሕፍት የመክፈቻ ሰዓቱን አራዘመ", "አዲሱ የብስክሌት መንገድ ሰኞ ይከፈታል",
           "የሳምንቱ መጨረሻ ትርኢት ሪከርድ ጎብኚዎችን አስተናገደ", "የምሽት ባቡር ወደ ክልሉ መስመር ተመለሰ"),
    "af": ("Die stadsbiblioteek verleng sy oopmaaktye", "Nuwe fietsroete open Maandag",
           "Naweekmark lok rekordgetal besoekers", "Nagtrein keer terug na die streekslyn"),
    "sw": ("Maktaba ya mji yaongeza saa za kufunguliwa", "Njia mpya ya baiskeli kufunguliwa Jumatatu",
           "Maonyesho ya wikendi yavunja rekodi ya wageni", "Treni ya usiku yarejea kwenye njia ya mkoa"),
}
_DEMO_SOURCES = ("Demo Press", "Demo Radio", "Demo Daily", "Demo Times")


def news(language: str, now: datetime) -> dict:
    lines = _HEADLINES.get(language) or _HEADLINES.get(language.split("-")[0]) or _HEADLINES["en"]
    items = [
        {
            "title": title,
            "source": _DEMO_SOURCES[i % len(_DEMO_SOURCES)],
            "published": (now - timedelta(minutes=12 + 37 * i)).isoformat(timespec="minutes"),
            "host": "",
        }
        for i, title in enumerate(lines)
    ]
    return {"items": items, "sources": len(items)}
