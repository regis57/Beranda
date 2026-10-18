"""How a heard sentence is matched to a built-in or own phrase: the cases people actually hit."""

from datetime import UTC, datetime

import pytest

from beranda.config import VoiceCommand
from beranda.providers import voice

NOW = datetime(2026, 10, 17, 9, tzinfo=UTC)


def _answer(text, language, stations):
    return voice.answer(text, language=language, now=NOW, stations=stations, weather=None)


def test_every_built_in_phrase_gives_its_own_intent():
    # The guide prints these phrases under their action; each one must really do that action.
    wrong = []
    for lang, table in voice._INTENTS.items():
        for intent, phrases in table.items():
            for phrase in phrases:
                got = voice.parse_intent(phrase, lang)
                if not got or got["intent"] != intent:
                    wrong.append((lang, phrase, intent, got))
    assert wrong == []


@pytest.mark.parametrize(
    ("text", "language", "names"),
    [
        ("play the radio", "en", ["France Inter", "FIP"]),
        ("mets la radio", "fr", ["France Inter", "FIP"]),
        ("joue la radio", "fr", ["France Inter", "FIP"]),
        ("remets la radio", "fr", ["France Inter", "FIP"]),
        ("spiele das radio", "de", ["Deutschlandfunk", "SWR3"]),
        ("pon la radio", "es", ["Cadena SER", "Los 40"]),
        ("metti la radio", "it", ["Rai Due", "Deejay"]),
        ("põe a rádio", "pt", ["Antena 1", "TSF"]),
    ],
)
def test_asking_for_the_radio_with_no_name_plays_the_first_favourite(text, language, names):
    stations = [{"name": n, "url": f"http://x/{i}", "uuid": str(i)} for i, n in enumerate(names)]
    got = _answer(text, language, stations)
    assert got["action"] and got["action"]["name"] == names[0], got


def test_a_station_name_with_radio_in_it_still_wins():
    stations = [{"name": "France Inter", "url": "a"}, {"name": "BBC Radio 4", "url": "b"}]
    assert _answer("play radio 4", "en", stations)["action"]["name"] == "BBC Radio 4"


def test_an_unknown_name_is_still_not_found():
    stations = [{"name": "France Inter", "url": "a"}]
    assert _answer("play zebulon", "en", stations)["action"] is None


def test_a_curly_apostrophe_typed_on_a_phone_matches_a_straight_one():
    cmd = VoiceCommand(phrase="what’s for tonight", action="say", reply="Pasta")
    assert voice.match_custom("what's for tonight", [cmd]) is cmd
    assert voice.parse_intent("qu’est-ce que j’ai aujourd’hui", "fr") == {"intent": "agenda"}


def test_accents_written_by_the_speech_service_do_not_matter():
    assert voice.parse_intent("les prévisions", "fr") == {"intent": "weather"}
    assert voice.parse_intent("para de falar", "pt") == {"intent": "quiet"}


def test_a_trigger_inside_a_longer_word_does_not_count():
    assert voice.parse_intent("play times radio", "en") == {"intent": "radio_play", "query": "times radio"}


@pytest.mark.parametrize(
    ("text", "language", "intent"),
    [("quelle heure est-il", "fr-FR", "time"), ("wie spät ist es", "de-DE", "time"), ("que horas são", "pt-PT", "time")],
)
def test_a_regional_language_code_understands_the_base_language(text, language, intent):
    assert voice.parse_intent(text, language) == {"intent": intent}
