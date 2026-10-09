"""The optional, always-listening voice service: wake word -> speech-to-text -> one of
Beranda's own actions -> text-to-speech. It is a *second* process (its own systemd service,
installed only with `install.sh --with-voice`), never the web server itself, and it talks to
Beranda only through the same local admin API your phone uses.

Everything below `main()` is plain glue with no audio in it, so it is fully covered by tests
on any machine. `main()` is the thin, real-hardware part - a microphone, openWakeWord, Vosk
and Piper - which could not be exercised in this development environment (no physical
microphone or speaker here); expect to adjust it once you can try it on a real Raspberry Pi.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from . import config as config_mod
from .providers.voice import parse_intent

log = logging.getLogger(__name__)

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
        "screen_restarting": "Restarting the screen.",
        "unknown": "Sorry, I didn't understand.",
    },
    "fr": {
        "weather_unknown": "Je n'ai pas la météo pour le moment.",
        "weather": "Il fait {temp} degrés, {sky}.",
        "time": "Il est {time}.",
        "radio_playing": "Je lance {name}.",
        "radio_not_found": "Je n'ai pas trouvé cette station dans vos favorites.",
        "radio_stopped": "Arrêté.",
        "screen_restarting": "Je redémarre l'écran.",
        "unknown": "Désolé, je n'ai pas compris.",
    },
    "de": {
        "weather_unknown": "Ich habe gerade keine Wetterdaten.",
        "weather": "Es sind {temp} Grad, {sky}.",
        "time": "Es ist {time} Uhr.",
        "radio_playing": "Ich spiele {name}.",
        "radio_not_found": "Diesen Sender habe ich nicht in deinen Favoriten gefunden.",
        "radio_stopped": "Gestoppt.",
        "screen_restarting": "Der Bildschirm startet neu.",
        "unknown": "Entschuldigung, das habe ich nicht verstanden.",
    },
    "es": {
        "weather_unknown": "No tengo el tiempo en este momento.",
        "weather": "Hace {temp} grados, {sky}.",
        "time": "Son las {time}.",
        "radio_playing": "Reproduciendo {name}.",
        "radio_not_found": "No encontré esa emisora en tus favoritas.",
        "radio_stopped": "Detenido.",
        "screen_restarting": "Reiniciando la pantalla.",
        "unknown": "Lo siento, no entendí eso.",
    },
    "it": {
        "weather_unknown": "Al momento non ho il meteo.",
        "weather": "Ci sono {temp} gradi, {sky}.",
        "time": "Sono le {time}.",
        "radio_playing": "Sto riproducendo {name}.",
        "radio_not_found": "Non ho trovato quella stazione tra i tuoi preferiti.",
        "radio_stopped": "Fermato.",
        "screen_restarting": "Riavvio lo schermo.",
        "unknown": "Scusa, non ho capito.",
    },
    "pt": {
        "weather_unknown": "Não tenho a meteorologia neste momento.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "A tocar {name}.",
        "radio_not_found": "Não encontrei essa estação nas suas favoritas.",
        "radio_stopped": "Parado.",
        "screen_restarting": "A reiniciar o ecrã.",
        "unknown": "Desculpe, não entendi.",
    },
    "pt-BR": {
        "weather_unknown": "Não tenho a previsão agora.",
        "weather": "Estão {temp} graus, {sky}.",
        "time": "São as {time}.",
        "radio_playing": "Tocando {name}.",
        "radio_not_found": "Não encontrei essa rádio nas suas favoritas.",
        "radio_stopped": "Parado.",
        "screen_restarting": "Reiniciando a tela.",
        "unknown": "Desculpe, não entendi.",
    },
    "ar": {
        "weather_unknown": "لا تتوفر لدي حالة الطقس الآن.",
        "weather": "الحرارة {temp} درجة، {sky}.",
        "time": "الساعة الآن {time}.",
        "radio_playing": "تشغيل {name}.",
        "radio_not_found": "لم أجد هذه المحطة بين مفضلاتك.",
        "radio_stopped": "تم التوقف.",
        "screen_restarting": "تتم إعادة تشغيل الشاشة.",
        "unknown": "عذرًا، لم أفهم ذلك.",
    },
    "sw": {
        "weather_unknown": "Sina taarifa za hali ya hewa sasa hivi.",
        "weather": "Ni nyuzijoto {temp}, {sky}.",
        "time": "Ni saa {time}.",
        "radio_playing": "Ninacheza {name}.",
        "radio_not_found": "Sikuipata kituo hicho kwenye vipendwa vyako.",
        "radio_stopped": "Imesimama.",
        "screen_restarting": "Skrini inaanzishwa upya.",
        "unknown": "Samahani, sikuelewa.",
    },
    "id": {
        "weather_unknown": "Saya tidak punya data cuaca saat ini.",
        "weather": "Suhunya {temp} derajat, {sky}.",
        "time": "Sekarang jam {time}.",
        "radio_playing": "Memutar {name}.",
        "radio_not_found": "Saya tidak menemukan stasiun itu di favorit Anda.",
        "radio_stopped": "Dihentikan.",
        "screen_restarting": "Memulai ulang layar.",
        "unknown": "Maaf, saya tidak mengerti.",
    },
}


def _t(language: str, key: str, **kw) -> str:
    table = _RESPONSES.get(language) or _RESPONSES["en"]
    return table.get(key, _RESPONSES["en"][key]).format(**kw)


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _best_station(stations: list[dict], query: str) -> dict | None:
    """The saved favourite whose name is closest to what was heard, if any is close enough."""
    if not query or not stations:
        return None
    best = max(stations, key=lambda s: _similar(s.get("name", ""), query))
    return best if _similar(best.get("name", ""), query) >= MATCH_THRESHOLD else None


async def handle_intent(intent: dict, *, client: httpx.AsyncClient, language: str, timezone: str) -> str:
    """Carry out `intent` against Beranda's own local admin API; return what to say back."""
    name = intent["intent"]
    if name == "weather":
        state = (await client.get("/api/state")).json()
        weather = state.get("weather")
        if not weather:
            return _t(language, "weather_unknown")
        return _t(language, "weather", temp=round(weather["temperature"]), sky=weather.get("summary", ""))
    if name == "time":
        now = datetime.now(ZoneInfo(timezone))
        return _t(language, "time", time=now.strftime("%H:%M"))
    if name == "radio_play":
        cfg = (await client.get("/api/admin/config")).json()["config"]
        station = _best_station(cfg.get("radio", {}).get("stations", []), intent.get("query", ""))
        if station is None:
            return _t(language, "radio_not_found")
        await client.post("/api/admin/radio-play", json=station)
        return _t(language, "radio_playing", name=station["name"])
    if name == "radio_stop":
        await client.post("/api/admin/radio-stop")
        return _t(language, "radio_stopped")
    if name == "restart_screen":
        await client.post("/api/admin/system/restart-screen")
        return _t(language, "screen_restarting")
    return _t(language, "unknown")


@dataclass
class Settings:
    base_url: str
    pin: str
    language: str
    timezone: str
    wake_word: str


def _speak(text: str, piper_model: str) -> None:
    """Synthesise `text` with the `piper` command-line voice and play it with `aplay`.

    Both are plain external tools (like the `mpv` radio already uses), so there is nothing
    Python-specific to get wrong here, and nothing is kept running or buffered between calls.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
        subprocess.run(
            ["piper", "--model", piper_model, "--output_file", wav.name],
            input=text.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(["aplay", "-q", wav.name], check=True)


def _listen_once(vosk_model, wake_word: str):  # pragma: no cover - needs a real microphone
    """Block until the wake word is heard, then return the sentence said right after it.

    Reads raw 16kHz mono PCM from `arecord` (already on every Raspberry Pi OS install),
    feeds it to openWakeWord until the wake word fires, then to a fresh Vosk recognizer
    until it has a confident final result.
    """
    import openwakeword
    import vosk

    oww = openwakeword.Model(wakeword_models=[wake_word])
    recogniser = vosk.KaldiRecognizer(vosk_model, 16000)
    chunk = 1280  # 80ms of 16-bit mono audio at 16kHz, openWakeWord's own frame size
    with subprocess.Popen(
        ["arecord", "-q", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE,
    ) as mic:
        heard_wake_word = False
        while True:
            data = mic.stdout.read(chunk * 2)
            if not data:
                return ""
            if not heard_wake_word:
                scores = oww.predict(data)
                if max(scores.values()) > 0.5:
                    heard_wake_word = True
                continue
            if recogniser.AcceptWaveform(data):
                import json

                return json.loads(recogniser.Result()).get("text", "")


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - needs real audio hardware
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s voice: %(message)s")
    parser = argparse.ArgumentParser(prog="beranda-voice", description="Beranda's offline voice control")
    parser.add_argument("--config", type=Path, help="path to config.toml")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080", help="where Beranda itself is serving")
    parser.add_argument("--vosk-model", required=True, help="path to a Vosk speech model for your language")
    parser.add_argument("--piper-model", required=True, help="path to a Piper voice (.onnx) for your language")
    args = parser.parse_args(argv)

    cfg = config_mod.load(args.config)
    if not cfg.voice_enabled:
        log.info("voice control is turned off in the settings page; nothing to do")
        return

    import asyncio

    import vosk

    vosk.SetLogLevel(-1)
    vosk_model = vosk.Model(args.vosk_model)
    settings = Settings(
        base_url=args.base_url, pin=cfg.admin_pin, language=cfg.language,
        timezone=cfg.location.timezone, wake_word=cfg.voice_wake_word,
    )
    log.info("listening for the wake word %r", settings.wake_word)

    async def handle(text: str) -> None:
        intent = parse_intent(text, settings.language)
        if intent is None:
            return
        headers = {"X-Beranda-Pin": settings.pin} if settings.pin else {}
        async with httpx.AsyncClient(base_url=settings.base_url, headers=headers, timeout=8) as client:
            reply = await handle_intent(
                intent, client=client, language=settings.language, timezone=settings.timezone
            )
        _speak(reply, args.piper_model)

    while True:
        text = _listen_once(vosk_model, settings.wake_word)
        if text:
            log.info("heard: %r", text)
            asyncio.run(handle(text))


if __name__ == "__main__":
    sys.exit(main())
