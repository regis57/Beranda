"""A screen opened with ?lang= listens in that language, so the Pi must match its phrases in it too."""

from dataclasses import replace

from fastapi.testclient import TestClient

from beranda.app import create_app
from beranda.config import Config


def _client(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "cache", demo=True, language="en", voice_enabled=True,
                  news_enabled=False, history_enabled=False)
    return TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=("127.0.0.1", 50000))


def test_the_language_the_screen_listened_in_is_used(tmp_path):
    reply = _client(tmp_path).post("/api/voice", json={"text": "quelle heure est-il", "language": "fr-FR"}).json()
    assert reply["intent"] == "time"


def test_without_a_language_the_saved_one_is_used(tmp_path):
    reply = _client(tmp_path).post("/api/voice", json={"text": "what time is it"}).json()
    assert reply["intent"] == "time"


def test_a_strange_language_value_falls_back_to_the_saved_one(tmp_path):
    reply = _client(tmp_path).post("/api/voice", json={"text": "what time is it", "language": "../../x"}).json()
    assert reply["intent"] == "time"
