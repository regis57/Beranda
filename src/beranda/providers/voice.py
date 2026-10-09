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
        "radio_next": ("next station", "next radio", "skip"),
        "radio_prev": ("previous station", "last station", "go back"),
        "volume_up": ("volume up", "louder", "turn it up"),
        "volume_down": ("volume down", "quieter", "turn it down"),
        "tv": ("tv tonight", "what's on tonight", "on tv", "television"),
    },
    "fr": {
        "weather": ("quel temps fait-il", "météo", "previsions"),
        "time": ("quelle heure est-il", "heure"),
        "radio_stop": ("coupe la radio", "arrête la radio", "silence", "arrête", "stop"),
        "radio_play": ("joue", "mets", "écoute"),
        "radio_next": ("station suivante", "radio suivante", "suivante", "suivant"),
        "radio_prev": ("station précédente", "radio précédente", "précédente", "précédent"),
        "volume_up": ("plus fort", "monte le son", "augmente le volume"),
        "volume_down": ("moins fort", "baisse le son", "baisse le volume"),
        "tv": ("à la télé", "programme tv", "programme télé", "télévision"),
    },
    "de": {
        "weather": ("wie ist das wetter", "wetter", "vorhersage"),
        "time": ("wie spät ist es", "uhrzeit", "zeit"),
        "radio_stop": ("radio aus", "stopp", "stop", "leise"),
        "radio_play": ("spiele", "spiel"),
        "radio_next": ("nächster sender", "nächste station", "nächster"),
        "radio_prev": ("vorheriger sender", "letzter sender", "zurück"),
        "volume_up": ("lauter",),
        "volume_down": ("leiser",),
        "tv": ("fernsehprogramm", "im fernsehen", "tv-programm", "fernsehen"),
    },
    "es": {
        "weather": ("qué tiempo hace", "tiempo", "pronóstico"),
        "time": ("qué hora es", "hora"),
        "radio_stop": ("para la radio", "detén la radio", "silencio", "para"),
        "radio_play": ("pon", "reproduce", "escucha"),
        "radio_next": ("siguiente emisora", "siguiente"),
        "radio_prev": ("emisora anterior", "anterior"),
        "volume_up": ("sube el volumen", "más fuerte", "más alto", "sube"),
        "volume_down": ("baja el volumen", "más bajo", "baja"),
        "tv": ("en la tele", "programa de tv", "televisión"),
    },
    "it": {
        "weather": ("che tempo fa", "meteo", "previsioni"),
        "time": ("che ora è", "ora"),
        "radio_stop": ("ferma la radio", "silenzio", "stop"),
        "radio_play": ("metti", "riproduci", "ascolta"),
        "radio_next": ("stazione successiva", "successiva", "prossima"),
        "radio_prev": ("stazione precedente", "precedente"),
        "volume_up": ("alza il volume", "più forte", "volume su"),
        "volume_down": ("abbassa il volume", "più piano", "volume giù"),
        "tv": ("stasera in tv", "programma tv", "in tv", "televisione"),
    },
    "pt": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para a rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
        "radio_next": ("estação seguinte", "seguinte"),
        "radio_prev": ("estação anterior", "anterior"),
        "volume_up": ("aumenta o volume", "mais alto", "mais forte"),
        "volume_down": ("diminui o volume", "mais baixo", "mais fraco"),
        "tv": ("na televisão", "programação", "na tv", "televisão"),
    },
    "pt-BR": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para o rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
        "radio_next": ("rádio seguinte", "seguinte", "próxima"),
        "radio_prev": ("rádio anterior", "anterior"),
        "volume_up": ("aumenta o volume", "mais alto", "mais forte"),
        "volume_down": ("diminui o volume", "mais baixo", "mais fraco"),
        "tv": ("na televisão", "programação", "na tv", "televisão"),
    },
    "ar": {
        "weather": ("كيف حال الطقس", "الطقس", "توقعات"),
        "time": ("كم الساعة", "الوقت"),
        "radio_stop": ("أوقف الراديو", "صمت", "قف"),
        "radio_play": ("شغل", "استمع"),
        "radio_next": ("المحطة التالية", "التالي"),
        "radio_prev": ("المحطة السابقة", "السابق"),
        "volume_up": ("ارفع الصوت",),
        "volume_down": ("اخفض الصوت",),
        "tv": ("برنامج التلفاز", "على التلفاز", "التلفزيون"),
    },
    "sw": {
        "weather": ("hali ya hewa", "utabiri"),
        "time": ("saa ngapi", "muda"),
        "radio_stop": ("zima redio", "kimya", "simama"),
        "radio_play": ("cheza", "sikiliza"),
        "radio_next": ("kituo kinachofuata", "kinachofuata"),
        "radio_prev": ("kituo kilichotangulia", "kilichotangulia"),
        "volume_up": ("ongeza sauti",),
        "volume_down": ("punguza sauti",),
        "tv": ("kwenye tv", "televisheni"),
    },
    "id": {
        "weather": ("bagaimana cuacanya", "cuaca", "ramalan"),
        "time": ("jam berapa", "waktu"),
        "radio_stop": ("matikan radio", "diam", "berhenti"),
        "radio_play": ("putar", "dengarkan"),
        "radio_next": ("stasiun berikutnya", "berikutnya"),
        "radio_prev": ("stasiun sebelumnya", "sebelumnya"),
        "volume_up": ("naikkan volume", "lebih keras"),
        "volume_down": ("turunkan volume", "lebih pelan"),
        "tv": ("acara tv", "di tv", "televisi"),
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
        "ok": "OK.",
        "tv": "Tonight on TV: {list}.",
        "tv_none": "I have no TV programme for tonight.",
    },
    "fr": {
        "weather_unknown": "Je n'ai pas la météo pour le moment.",
        "weather": "Il fait {temp} degrés, {sky}.",
        "time": "Il est {time}.",
        "radio_playing": "Je lance {name}.",
        "radio_not_found": "Je n'ai pas trouvé cette station dans vos favorites.",
        "radio_stopped": "Arrêté.",
        "unknown": "Désolé, je n'ai pas compris.",
        "ok": "D'accord.",
        "tv": "Ce soir à la télé : {list}.",
        "tv_none": "Je n'ai aucun programme télé pour ce soir.",
    },
    "de": {
        "weather_unknown": "Ich habe gerade keine Wetterdaten.",
        "weather": "Es sind {temp} Grad, {sky}.",
        "time": "Es ist {time} Uhr.",
        "radio_playing": "Ich spiele {name}.",
        "radio_not_found": "Diesen Sender habe ich nicht in deinen Favoriten gefunden.",
        "radio_stopped": "Gestoppt.",
        "unknown": "Entschuldigung, das habe ich nicht verstanden.",
        "ok": "Okay.",
        "tv": "Heute Abend im Fernsehen: {list}.",
        "tv_none": "Ich habe kein Fernsehprogramm für heute Abend.",
    },
    "es": {
        "weather_unknown": "No tengo el tiempo en este momento.",
        "weather": "Hace {temp} grados, {sky}.",
        "time": "Son las {time}.",
        "radio_playing": "Reproduciendo {name}.",
        "radio_not_found": "No encontré esa emisora en tus favoritas.",
        "radio_stopped": "Detenido.",
        "unknown": "Lo siento, no entendí eso.",
        "ok": "Vale.",
        "tv": "Esta noche en la tele: {list}.",
        "tv_none": "No tengo programación de TV para esta noche.",
    },
    "it": {
        "weather_unknown": "Al momento non ho il meteo.",
        "weather": "Ci sono {temp} gradi, {sky}.",
        "time": "Sono le {time}.",
        "radio_playing": "Sto riproducendo {name}.",
        "radio_not_found": "Non ho trovato quella stazione tra i tuoi preferiti.",
        "radio_stopped": "Fermato.",
        "unknown": "Scusa, non ho capito.",
        "ok": "Va bene.",
        "tv": "Stasera in TV: {list}.",
        "tv_none": "Non ho programmi TV per stasera.",
    },
    "pt": {
        "weather_unknown": "Não tenho a meteorologia neste momento.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "A tocar {name}.",
        "radio_not_found": "Não encontrei essa estação nas suas favoritas.",
        "radio_stopped": "Parado.",
        "unknown": "Desculpe, não entendi.",
        "ok": "Está bem.",
        "tv": "Esta noite na TV: {list}.",
        "tv_none": "Não tenho programação de TV para esta noite.",
    },
    "pt-BR": {
        "weather_unknown": "Não tenho a previsão agora.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "Tocando {name}.",
        "radio_not_found": "Não encontrei essa rádio nas suas favoritas.",
        "radio_stopped": "Parado.",
        "unknown": "Desculpe, não entendi.",
        "ok": "Tudo bem.",
        "tv": "Hoje à noite na TV: {list}.",
        "tv_none": "Não tenho programação de TV para hoje à noite.",
    },
    "ar": {
        "weather_unknown": "لا تتوفر لدي حالة الطقس الآن.",
        "weather": "الحرارة {temp} درجة، {sky}.",
        "time": "الساعة الآن {time}.",
        "radio_playing": "تشغيل {name}.",
        "radio_not_found": "لم أجد هذه المحطة بين مفضلاتك.",
        "radio_stopped": "تم التوقف.",
        "unknown": "عذرًا، لم أفهم ذلك.",
        "ok": "حسنًا.",
        "tv": "هذا المساء على التلفاز: {list}.",
        "tv_none": "ليس لدي برنامج تلفزيوني لهذا المساء.",
    },
    "sw": {
        "weather_unknown": "Sina taarifa za hali ya hewa sasa hivi.",
        "weather": "Ni nyuzijoto {temp}, {sky}.",
        "time": "Ni saa {time}.",
        "radio_playing": "Ninacheza {name}.",
        "radio_not_found": "Sikuipata kituo hicho kwenye vipendwa vyako.",
        "radio_stopped": "Imesimama.",
        "unknown": "Samahani, sikuelewa.",
        "ok": "Sawa.",
        "tv": "Usiku huu kwenye TV: {list}.",
        "tv_none": "Sina kipindi cha TV cha usiku huu.",
    },
    "id": {
        "weather_unknown": "Saya tidak punya data cuaca saat ini.",
        "weather": "Suhunya {temp} derajat, {sky}.",
        "time": "Sekarang jam {time}.",
        "radio_playing": "Memutar {name}.",
        "radio_not_found": "Saya tidak menemukan stasiun itu di favorit Anda.",
        "radio_stopped": "Dihentikan.",
        "unknown": "Maaf, saya tidak mengerti.",
        "ok": "Baik.",
        "tv": "Malam ini di TV: {list}.",
        "tv_none": "Saya tidak punya acara TV untuk malam ini.",
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


def default_commands(language: str) -> dict[str, list[str]]:
    """The built-in phrases per action, in the display language, for the settings page to show."""
    table = _INTENTS.get(language) or _INTENTS.get(language.split("-")[0]) or _INTENTS["en"]
    return {intent: list(phrases) for intent, phrases in table.items()}


def match_custom(text: str, commands) -> object | None:
    """The user's own command whose phrase is contained in what was said (longest phrase first).

    Own phrases win over the built-in ones: if you taught Beranda "good night", that is what
    "good night" does, whatever the built-in list says.
    """
    heard = _normalise(text)
    for cmd in sorted(commands, key=lambda c: -len(c.phrase)):
        phrase = _normalise(cmd.phrase)
        if phrase and phrase in heard:
            return cmd
    return None


def _tv_reply(language: str, tv: dict | None) -> str:
    programmes = (tv or {}).get("programmes") or []
    if not programmes:
        return _t(language, "tv_none")
    listing = ", ".join(f"{p['channel']} : {p['title']} ({p['start']})" for p in programmes[:4])
    return _t(language, "tv", list=listing)


def answer(
    text: str,
    *,
    language: str,
    now: datetime,
    stations: list[dict],
    weather: dict | None,
    tv: dict | None = None,
    commands=(),
) -> dict:
    """What to say and do for the sentence `text`.

    Returns {"intent": name|None, "reply": text to speak, "action": None | {"type": ..., ...}}.
    The page itself plays or stops the radio and moves the volume (the sound must come out of
    the tablet, and only the page knows which station is on).
    """
    custom = match_custom(text, commands)
    if custom is not None and custom.action == "say":
        return {"intent": "say", "reply": custom.reply, "action": None}
    if custom is not None:
        name, query, wanted = custom.action, "", custom.station
    else:
        intent = parse_intent(text, language)
        if intent is None:
            return {"intent": None, "reply": _t(language, "unknown"), "action": None}
        name, query, wanted = intent["intent"], intent.get("query", ""), ""

    if name == "weather":
        if not weather:
            return {"intent": name, "reply": _t(language, "weather_unknown"), "action": None}
        current = weather["current"]
        reply = _t(language, "weather", temp=round(current["temp"]), sky=sky_text(language, current["code"]).lower())
        return {"intent": name, "reply": reply, "action": None}
    if name == "time":
        return {"intent": name, "reply": _t(language, "time", time=now.strftime("%H:%M")), "action": None}
    if name == "tv":
        return {"intent": name, "reply": _tv_reply(language, tv), "action": None}
    if name == "radio_stop":
        return {"intent": name, "reply": _t(language, "radio_stopped"), "action": {"type": "radio_stop"}}
    if name in ("radio_next", "radio_prev", "volume_up", "volume_down"):
        return {"intent": name, "reply": _t(language, "ok"), "action": {"type": name}}

    # radio_play: a favourite chosen on the settings page, or the one named out loud.
    if wanted:
        station = next((s for s in stations if s.get("uuid") == wanted), None)
    else:
        station = best_station(stations, query)
    if station is None:
        return {"intent": name, "reply": _t(language, "radio_not_found"), "action": None}
    return {
        "intent": name,
        "reply": _t(language, "radio_playing", name=station["name"]),
        "action": {"type": "radio_play", "uuid": station.get("uuid", ""), "url": station["url"], "name": station["name"]},
    }
