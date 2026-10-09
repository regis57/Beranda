"""Turning a recognised sentence into one of Beranda's own actions.

This is the only "understanding" voice control needs: no cloud assistant, no language model,
just a short list of trigger words per language matched against the plain text the offline
speech-to-text already gives us. It is deliberately small - a handful of things said around
a kitchen (the weather, the time, a favourite station, the screen), not a general assistant.
"""

from __future__ import annotations

import re
import unicodedata

# openWakeWord ships pretrained models for these three wake phrases; Beranda does not train
# its own, so picking a wake word on the settings page means picking one of these.
WAKE_WORDS = ("alexa", "hey_jarvis", "hey_mycroft")
DEFAULT_WAKE_WORD = "hey_jarvis"

# Longer phrases are tried before shorter ones, so e.g. "turn off the radio" is not swallowed
# by the shorter "stop" trigger first. "radio_play" is special: whatever is left of the
# sentence after removing its trigger phrase is kept as the station name to search for.
_INTENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "weather": ("what's the weather", "weather", "forecast"),
        "time": ("what time is it", "time"),
        "radio_stop": ("turn off the radio", "stop the radio", "stop", "quiet"),
        "radio_play": ("play",),
        "restart_screen": ("restart the screen", "refresh the screen"),
    },
    "fr": {
        "weather": ("quel temps fait-il", "météo", "previsions"),
        "time": ("quelle heure est-il", "heure"),
        "radio_stop": ("coupe la radio", "arrête la radio", "silence", "arrête", "stop"),
        "radio_play": ("joue", "mets", "écoute"),
        "restart_screen": ("redémarre l'écran", "rafraîchis l'écran"),
    },
    "de": {
        "weather": ("wie ist das wetter", "wetter", "vorhersage"),
        "time": ("wie spät ist es", "uhrzeit", "zeit"),
        "radio_stop": ("radio aus", "stopp", "stop", "leise"),
        "radio_play": ("spiele", "spiel"),
        "restart_screen": ("bildschirm neu starten",),
    },
    "es": {
        "weather": ("qué tiempo hace", "tiempo", "pronóstico"),
        "time": ("qué hora es", "hora"),
        "radio_stop": ("para la radio", "detén la radio", "silencio", "para"),
        "radio_play": ("pon", "reproduce", "escucha"),
        "restart_screen": ("reinicia la pantalla",),
    },
    "it": {
        "weather": ("che tempo fa", "meteo", "previsioni"),
        "time": ("che ora è", "ora"),
        "radio_stop": ("ferma la radio", "silenzio", "stop"),
        "radio_play": ("metti", "riproduci", "ascolta"),
        "restart_screen": ("riavvia lo schermo",),
    },
    "pt": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para a rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
        "restart_screen": ("reinicia o ecrã",),
    },
    "pt-BR": {
        "weather": ("que tempo faz", "previsão", "meteorologia"),
        "time": ("que horas são", "hora"),
        "radio_stop": ("para o rádio", "silêncio", "para"),
        "radio_play": ("põe", "toca", "ouve"),
        "restart_screen": ("reinicia a tela",),
    },
    "ar": {
        "weather": ("كيف حال الطقس", "الطقس", "توقعات"),
        "time": ("كم الساعة", "الوقت"),
        "radio_stop": ("أوقف الراديو", "صمت", "قف"),
        "radio_play": ("شغل", "استمع"),
        "restart_screen": ("أعد تشغيل الشاشة",),
    },
    "sw": {
        "weather": ("hali ya hewa", "utabiri"),
        "time": ("saa ngapi", "muda"),
        "radio_stop": ("zima redio", "kimya", "simama"),
        "radio_play": ("cheza", "sikiliza"),
        "restart_screen": ("anzisha skrini upya",),
    },
    "id": {
        "weather": ("bagaimana cuacanya", "cuaca", "ramalan"),
        "time": ("jam berapa", "waktu"),
        "radio_stop": ("matikan radio", "diam", "berhenti"),
        "radio_play": ("putar", "dengarkan"),
        "restart_screen": ("mulai ulang layar",),
    },
}


def check_wake_word(value: object) -> str:
    text = str(value or DEFAULT_WAKE_WORD).strip().lower()
    if text not in WAKE_WORDS:
        raise ValueError(f"wake word must be one of {WAKE_WORDS}, got {text!r}")
    return text


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
