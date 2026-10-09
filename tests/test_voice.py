import pytest

from beranda.providers import voice


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("what's the weather today", "en", {"intent": "weather"}),
        ("what time is it", "en", {"intent": "time"}),
        ("play france inter", "en", {"intent": "radio_play", "query": "france inter"}),
        ("stop", "en", {"intent": "radio_stop"}),
        ("turn off the radio", "en", {"intent": "radio_stop"}),
        ("restart the screen", "en", {"intent": "restart_screen"}),
        ("quelle heure est-il", "fr", {"intent": "time"}),
        ("joue france musique", "fr", {"intent": "radio_play", "query": "france musique"}),
        ("arrête la radio", "fr", {"intent": "radio_stop"}),
        ("wie ist das wetter", "de", {"intent": "weather"}),
        ("bagaimana cuacanya", "id", {"intent": "weather"}),
        ("something unrelated entirely", "en", None),
        ("un langage que nous ne gérons pas", "xx", None),  # unknown language falls back to English
    ],
)
def test_parse_intent(text, language, expected):
    assert voice.parse_intent(text, language) == expected


def test_parse_intent_prefers_the_longest_matching_trigger():
    # "stop" alone would also match, but the longer phrase should win.
    assert voice.parse_intent("please turn off the radio now", "en") == {"intent": "radio_stop"}


def test_parse_intent_is_case_and_space_insensitive():
    assert voice.parse_intent("  PLAY   Nostalgie  ", "en") == {"intent": "radio_play", "query": "nostalgie"}


def test_parse_intent_of_empty_text_is_nothing():
    assert voice.parse_intent("", "en") is None
    assert voice.parse_intent("   ", "fr") is None


@pytest.mark.parametrize("bad", ["", "beranda", "HEY_JARVIS!", "ok google"])
def test_check_wake_word_rejects_anything_not_pretrained(bad):
    if bad == "":
        assert voice.check_wake_word(bad) == voice.DEFAULT_WAKE_WORD
    else:
        with pytest.raises(ValueError, match="wake word"):
            voice.check_wake_word(bad)


@pytest.mark.parametrize("word", voice.WAKE_WORDS)
def test_check_wake_word_accepts_the_pretrained_ones(word):
    assert voice.check_wake_word(word) == word
