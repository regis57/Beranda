from datetime import datetime

import pytest

from beranda import config
from beranda.providers import voice


@pytest.mark.parametrize(
    ("text", "language", "expected"),
    [
        ("what's the weather today", "en", {"intent": "weather"}),
        ("what time is it", "en", {"intent": "time"}),
        ("play france inter", "en", {"intent": "radio_play", "query": "france inter"}),
        ("stop", "en", {"intent": "radio_stop"}),
        ("turn off the radio", "en", {"intent": "radio_stop"}),
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


from zoneinfo import ZoneInfo

NOW = datetime(2026, 10, 8, 18, 5, tzinfo=ZoneInfo("Europe/Paris"))
STATIONS = [
    {"uuid": "a", "name": "France Inter", "url": "http://a.example/stream"},
    {"uuid": "b", "name": "FIP", "url": "http://b.example/stream"},
]
WEATHER = {"current": {"temp": 14.4, "code": 2}}


def ask(text, language="fr", stations=STATIONS, weather=WEATHER):
    return voice.answer(text, language=language, now=NOW, stations=stations, weather=weather)


def test_asking_for_a_station_by_name_plays_the_closest_favourite():
    result = ask("mets france inter")
    assert result["action"] == {"type": "radio_play", "uuid": "a", "url": "http://a.example/stream", "name": "France Inter"}
    assert "France Inter" in result["reply"]


def test_a_slightly_misheard_name_still_finds_the_station():
    assert ask("joue france intère")["action"]["uuid"] == "a"


def test_saying_play_with_no_name_plays_the_first_favourite():
    assert ask("joue")["action"]["uuid"] == "a"


def test_an_unknown_station_is_not_played():
    result = ask("joue radio zorglub inconnue")
    assert result["action"] is None and result["intent"] == "radio_play"


def test_no_favourites_means_nothing_to_play():
    assert ask("mets fip", stations=[])["action"] is None


def test_stop_tells_the_page_to_stop_the_radio():
    assert ask("arrête la radio")["action"] == {"type": "radio_stop"}


def test_the_weather_is_answered_in_the_users_language():
    reply = ask("quel temps fait-il")["reply"]
    assert "14" in reply and "partiellement nuageux" in reply


def test_the_weather_when_it_is_unknown():
    assert ask("météo", weather=None)["action"] is None


def test_the_time_is_spoken():
    assert ask("quelle heure est-il")["reply"] == "Il est 18:05."


def test_nonsense_gets_a_polite_answer_and_no_action():
    result = ask("blablabla")
    assert result["intent"] is None and result["action"] is None and result["reply"]


def test_every_spoken_reply_has_the_same_keys_in_every_language():
    english = set(voice._RESPONSES["en"])
    assert all(set(table) == english for table in voice._RESPONSES.values())


FAVOURITES = [
    {"uuid": "a", "name": "France Inter", "url": "http://a"},
    {"uuid": "b", "name": "Jak 101 FM", "url": "http://b"},
]


def hear(text, language="fr", **kw):
    return voice.answer(text, language=language, now=NOW, stations=FAVOURITES, weather=None, **kw)


@pytest.mark.parametrize(
    ("text", "language", "intent"),
    [
        ("station suivante", "fr", "radio_next"),
        ("station précédente", "fr", "radio_prev"),
        ("plus fort", "fr", "volume_up"),
        ("mets plus fort", "fr", "volume_up"),  # longer than "mets", so it is not a "play" request
        ("baisse le son", "fr", "volume_down"),
        ("next station", "en", "radio_next"),
        ("play next station", "en", "radio_next"),
        ("quieter", "en", "volume_down"),
        ("leiser", "de", "volume_down"),
        ("qu'y a-t-il à la télé", "fr", "tv"),
    ],
)
def test_the_new_builtin_commands(text, language, intent):
    assert voice.parse_intent(text, language)["intent"] == intent


def test_page_actions_for_next_previous_and_volume():
    assert hear("station suivante")["action"] == {"type": "radio_next"}
    assert hear("moins fort")["action"] == {"type": "volume_down"}


def test_tv_answer_reads_tonights_programmes_or_says_there_are_none():
    tv = {"status": "ok", "programmes": [{"channel": "France 2", "title": "Journal", "start": "20:00", "stop": "20:45"}]}
    assert "France 2" in hear("à la télé", tv=tv)["reply"]
    assert hear("à la télé", tv=None)["reply"] == "Je n'ai aucun programme télé pour ce soir."


def test_an_own_phrase_can_just_answer():
    cmd = config.VoiceCommand(phrase="bonne nuit", action="say", reply="Dors bien")
    r = hear("Allez, bonne nuit la maison", commands=(cmd,))
    assert (r["reply"], r["action"]) == ("Dors bien", None)


def test_an_own_phrase_can_start_one_chosen_favourite():
    cmd = config.VoiceCommand(phrase="réveil", action="radio_play", station="b")
    r = hear("réveil", commands=(cmd,))
    assert r["action"]["name"] == "Jak 101 FM"


def test_an_own_phrase_pointing_to_a_removed_favourite_says_so():
    cmd = config.VoiceCommand(phrase="réveil", action="radio_play", station="gone")
    r = hear("réveil", commands=(cmd,))
    assert r["action"] is None
    assert "favorites" in r["reply"]


def test_own_phrases_beat_the_builtin_ones_and_the_longest_wins():
    short = config.VoiceCommand(phrase="mets", action="say", reply="court")
    long = config.VoiceCommand(phrase="mets la météo", action="say", reply="long")
    assert hear("mets la météo", commands=(short, long))["reply"] == "long"


def test_default_commands_follow_the_language_and_fall_back_to_english():
    assert "météo" in voice.default_commands("fr")["weather"]
    assert "weather" in voice.default_commands("xx")["weather"]
