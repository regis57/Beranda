"""More phrases, in every voice language, and the wake word."""

from datetime import UTC, datetime

from beranda.providers import voice

NEW = ("read_day", "date", "agenda", "tomorrow", "news", "bigger", "smaller", "contrast_on", "contrast_off", "quiet")


def test_every_voice_language_has_every_new_phrase():
    for lang, phrases in voice._INTENTS.items():
        for intent in NEW:
            assert phrases.get(intent), (lang, intent)


def test_the_new_phrases_are_done_by_the_page():
    for intent in NEW:
        text = voice._INTENTS["en"][intent][0]
        answer = voice.answer(text, language="en", now=datetime(2026, 10, 17, 9, tzinfo=UTC), stations=[], weather=None)
        assert answer == {"intent": intent, "reply": "", "action": {"type": intent}}


def test_longer_phrases_win_so_stop_talking_is_not_stop_the_radio():
    assert voice.parse_intent("stop talking", "en") == {"intent": "quiet"}
    assert voice.parse_intent("stop", "en") == {"intent": "radio_stop"}
    assert voice.parse_intent("qu'est-ce que j'ai demain", "fr") == {"intent": "tomorrow"}
    assert voice.parse_intent("lis les nouvelles", "fr") == {"intent": "news"}
