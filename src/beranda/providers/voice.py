"""Turning a spoken sentence into one of Beranda's own actions.

The tablet's browser listens and turns speech into text (that part is the browser's job, see
`voice.js`); the text then comes here. This is the only "understanding" voice control needs:
no assistant, no language model, just a short list of trigger words per language. It is
deliberately small - a handful of things said around a kitchen (the weather, the time, a
favourite station, stopping the radio), not a general assistant.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent.parent / "web" / "i18n"

# Longer phrases are tried before shorter ones, so e.g. "turn off the radio" is not swallowed
# by the shorter "stop" trigger first. "radio_play" is special: whatever is left of the
# sentence after removing its trigger phrase is kept as the station name to search for.
_INTENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "weather": ("what's the weather", "weather", "forecast"),
        "time": ("what time is it", "time"),
        "radio_stop": ("turn off the radio", "stop the radio", "stop", "quiet"),
        "radio_play": ("play",),
    },
    "fr": {
        "weather": ("quel temps fait-il", "météo", "previsions"),
        "time": ("quelle heure est-il", "heure"),
        "radio_stop": ("coupe la radio", "arrête la radio", "silence", "arrête", "stop"),
        "radio_play": ("joue", "mets", "écoute"),
    },
    "de": {
        "weather": ("wie ist das wetter", "wetter", "vorhersage"),
        "time": ("wie spät ist es", "uhrzeit", "zeit"),
        "radio_stop": ("radio aus", "stopp", "stop", "leise"),
        "radio_play": ("spiele", "spiel"),
    },
    "es": {
        "weather": ("qué tiempo hace", "tiempo", "pronóstico"),
        "time": ("qué hora es", "hora"),
        "radio_stop": ("para la radio", "detén la radio", "silencio", "para"),
        "radio_play": ("pon", "reproduce", "escucha"),
    },
    "it": {
        "weather": ("che tempo fa", "meteo", "previsioni"),
        "time": ("che ora è", "ora"),
        "radio_stop": ("ferma la radio", "silenzio", "stop"),
        "radio_play": ("metti", "riproduci", "ascolta"),
    },
    "pt": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para a rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
    },
    "pt-BR": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para o rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
    },
    "ar": {
        "weather": ("كيف حال الطقس", "الطقس", "توقعات"),
        "time": ("كم الساعة", "الوقت"),
        "radio_stop": ("أوقف الراديو", "صمت", "قف"),
        "radio_play": ("شغل", "استمع"),
    },
    "sw": {
        "weather": ("hali ya hewa", "utabiri"),
        "time": ("saa ngapi", "muda"),
        "radio_stop": ("zima redio", "kimya", "simama"),
        "radio_play": ("cheza", "sikiliza"),
    },
    "id": {
        "weather": ("bagaimana cuacanya", "cuaca", "ramalan"),
        "time": ("jam berapa", "waktu"),
        "radio_stop": ("matikan radio", "diam", "berhenti"),
        "radio_play": ("putar", "dengarkan"),
    },
}


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    return re.sub(r"\s+", " ", text)


def parse_intent(text: str, language: str = "en") -> dict | None:
    """The first trigger phrase found in `text`, longest phrases checked first, or None."""
    text = _normalise(text)
    if not text:
        return None
    keywords = _INTENTS.get(language, _INTENTS["en"])
    candidates = sorted(
        ((intent, trig) for intent, trigs in keywords.items() for trig in trigs),
        key=lambda pair: -len(pair[1]),
    )
    for intent, trig in candidates:
        idx = text.find(trig)
        if idx == -1:
            continue
        if intent == "radio_play":
            remainder = (text[:idx] + text[idx + len(trig) :]).strip()
            return {"intent": intent, "query": remainder}
        return {"intent": intent}
    return None


# A heard station name rarely matches a saved favourite letter for letter (mishears, accents,
# word order); below this similarity we'd rather say "not found" than play the wrong station.
MATCH_THRESHOLD = 0.4

_RESPONSES: dict[str, dict[str, str]] = {
    "en": {
        "weather_unknown": "I don't have the weather right now.",
        "weather": "It's {temp} degrees, {sky}.",
        "time": "It's {time}.",
        "radio_playing": "Playing {name}.",
        "radio_not_found": "I couldn't find that station in your favourites.",
        "radio_stopped": "Stopped.",
        "unknown": "Sorry, I didn't understand.",
    },
    "fr": {
        "weather_unknown": "Je n'ai pas la météo pour le moment.",
        "weather": "Il fait {temp} degrés, {sky}.",
        "time": "Il est {time}.",
        "radio_playing": "Je lance {name}.",
        "radio_not_found": "Je n'ai pas trouvé cette station dans vos favorites.",
        "radio_stopped": "Arrêté.",
        "unknown": "Désolé, je n'ai pas compris.",
    },
    "de": {
        "weather_unknown": "Ich habe gerade keine Wetterdaten.",
        "weather": "Es sind {temp} Grad, {sky}.",
        "time": "Es ist {time} Uhr.",
        "radio_playing": "Ich spiele {name}.",
        "radio_not_found": "Diesen Sender habe ich nicht in deinen Favoriten gefunden.",
        "radio_stopped": "Gestoppt.",
        "unknown": "Entschuldigung, das habe ich nicht verstanden.",
    },
    "es": {
        "weather_unknown": "No tengo el tiempo en este momento.",
        "weather": "Hace {temp} grados, {sky}.",
        "time": "Son las {time}.",
        "radio_playing": "Reproduciendo {name}.",
        "radio_not_found": "No encontré esa emisora en tus favoritas.",
        "radio_stopped": "Detenido.",
        "unknown": "Lo siento, no entendí eso.",
    },
    "it": {
        "weather_unknown": "Al momento non ho il meteo.",
        "weather": "Ci sono {temp} gradi, {sky}.",
        "time": "Sono le {time}.",
        "radio_playing": "Sto riproducendo {name}.",
        "radio_not_found": "Non ho trovato quella stazione tra i tuoi preferiti.",
        "radio_stopped": "Fermato.",
        "unknown": "Scusa, non ho capito.",
    },
    "pt": {
        "weather_unknown": "Não tenho a meteorologia neste momento.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "A tocar {name}.",
        "radio_not_found": "Não encontrei essa estação nas suas favoritas.",
        "radio_stopped": "Parado.",
        "unknown": "Desculpe, não entendi.",
    },
    "pt-BR": {
        "weather_unknown": "Não tenho a previsão agora.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "Tocando {name}.",
        "radio_not_found": "Não encontrei essa rádio nas suas favoritas.",
        "radio_stopped": "Parado.",
        "unknown": "Desculpe, não entendi.",
    },
    "ar": {
        "weather_unknown": "لا تتوفر لدي حالة الطقس الآن.",
        "weather": "الحرارة {temp} درجة، {sky}.",
        "time": "الساعة الآن {time}.",
        "radio_playing": "تشغيل {name}.",
        "radio_not_found": "لم أجد هذه المحطة بين مفضلاتك.",
        "radio_stopped": "تم التوقف.",
        "unknown": "عذرًا، لم أفهم ذلك.",
    },
    "sw": {
        "weather_unknown": "Sina taarifa za hali ya hewa sasa hivi.",
        "weather": "Ni nyuzijoto {temp}, {sky}.",
        "time": "Ni saa {time}.",
        "radio_playing": "Ninacheza {name}.",
        "radio_not_found": "Sikuipata kituo hicho kwenye vipendwa vyako.",
        "radio_stopped": "Imesimama.",
        "unknown": "Samahani, sikuelewa.",
    },
    "id": {
        "weather_unknown": "Saya tidak punya data cuaca saat ini.",
        "weather": "Suhunya {temp} derajat, {sky}.",
        "time": "Sekarang jam {time}.",
        "radio_playing": "Memutar {name}.",
        "radio_not_found": "Saya tidak menemukan stasiun itu di favorit Anda.",
        "radio_stopped": "Dihentikan.",
        "unknown": "Maaf, saya tidak mengerti.",
    },
}



def _t(language: str, key: str, **kw) -> str:
    table = _RESPONSES.get(language) or _RESPONSES.get(language.split("-")[0]) or _RESPONSES["en"]
    return table.get(key, _RESPONSES["en"][key]).format(**kw)


def sky_text(language: str, code: int) -> str:
    """"Partly cloudy" for weather code 2, in the display's own translation (English if missing)."""
    for name in dict.fromkeys([language, language.split("-")[0], "en"]):
        try:
            strings = json.loads((I18N_DIR / f"{name}.json").read_text(encoding="utf-8"))
            return strings["wmo"][str(code)]
        except (OSError, ValueError, KeyError):
            continue
    return ""


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()


def best_station(stations: list[dict], query: str) -> dict | None:
    """The saved favourite whose name is closest to what was heard, if any is close enough.

    Saying just "play the radio" (no name) picks the first favourite.
    """
    if not stations:
        return None
    if not query.strip():
        return stations[0]
    best = max(stations, key=lambda s: _similar(s.get("name", ""), query))
    return best if _similar(best.get("name", ""), query) >= MATCH_THRESHOLD else None


def answer(text: str, *, language: str, now: datetime, stations: list[dict], weather: dict | None) -> dict:
    """What to say and do for the sentence `text`.

    Returns {"intent": name|None, "reply": text to speak, "action": None | {"type": ..., ...}}.
    The page itself plays or stops the radio (the sound must come out of the tablet).
    """
    intent = parse_intent(text, language)
    if intent is None:
        return {"intent": None, "reply": _t(language, "unknown"), "action": None}
    name = intent["intent"]
    if name == "weather":
        if not weather:
            return {"intent": name, "reply": _t(language, "weather_unknown"), "action": None}
        current = weather["current"]
        reply = _t(language, "weather", temp=round(current["temp"]), sky=sky_text(language, current["code"]).lower())
        return {"intent": name, "reply": reply, "action": None}
    if name == "time":
        return {"intent": name, "reply": _t(language, "time", time=now.strftime("%H:%M")), "action": None}
    if name == "radio_stop":
        return {"intent": name, "reply": _t(language, "radio_stopped"), "action": {"type": "radio_stop"}}
    station = best_station(stations, intent.get("query", ""))
    if station is None:
        return {"intent": name, "reply": _t(language, "radio_not_found"), "action": None}
    return {
        "intent": name,
        "reply": _t(language, "radio_playing", name=station["name"]),
        "action": {"type": "radio_play", "uuid": station.get("uuid", ""), "url": station["url"], "name": station["name"]},
    }
