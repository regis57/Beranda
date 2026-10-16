"""The Accessibility box: three switches that reach the screen, and "read me the day"."""

from dataclasses import replace

from fastapi.testclient import TestClient

from beranda.app import create_app
from beranda.config import Config, from_dict, to_dict
from beranda.providers import voice

HOME = ("192.168.1.20", 5000)


def test_the_three_switches_round_trip_through_the_settings_file():
    cfg = from_dict({"accessibility": {"large_text": True, "high_contrast": False, "read_aloud": True}})
    assert (cfg.a11y_large_text, cfg.a11y_high_contrast, cfg.a11y_read_aloud) == (True, False, True)
    assert to_dict(cfg)["accessibility"] == {"large_text": True, "high_contrast": False, "read_aloud": True}
    assert from_dict({}).a11y_large_text is False  # off unless asked for


def test_the_screen_is_told_which_switches_are_on(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "c", demo=True, a11y_high_contrast=True, news_enabled=False, history_enabled=False)
    state = TestClient(create_app(cfg), client=HOME).get("/api/state").json()
    assert state["accessibility"] == {"large_text": False, "high_contrast": True, "read_aloud": False}


def test_the_settings_page_saves_the_box(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False, history_enabled=False)
    client = TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=HOME)
    body = client.get("/api/admin/config").json()["config"]
    body["accessibility"] = {"large_text": True, "high_contrast": True, "read_aloud": True}
    assert client.put("/api/admin/config", json=body).status_code == 200
    assert "large_text = true" in (tmp_path / "config.toml").read_text()


def test_read_me_the_day_is_understood_in_every_voice_language():
    for lang, phrase in {"en": "read me the day", "fr": "lis-moi la journée", "de": "lies mir den tag vor",
                         "es": "léeme el día", "it": "leggimi la giornata", "pt": "lê-me o dia",
                         "pt-BR": "leia meu dia", "id": "bacakan hari ini", "sw": "nisomee siku",
                         "ar": "اقرأ لي اليوم"}.items():
        assert voice.parse_intent(phrase, lang) == {"intent": "read_day"}, lang


def test_read_me_the_day_is_left_to_the_page():
    """The page has the whole day on screen already: it speaks it itself, in its own words."""
    from datetime import UTC, datetime
    answer = voice.answer("read me the day", language="en", now=datetime(2026, 10, 16, 9, tzinfo=UTC), stations=[], weather=None)
    assert answer["action"] == {"type": "read_day"} and answer["reply"] == ""
