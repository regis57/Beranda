"""Ticked TV channels keep their usual name (some guides only give numbers as ids)."""

from dataclasses import replace

from fastapi.testclient import TestClient

from beranda import config
from beranda.app import create_app
from beranda.config import Config


def test_names_are_kept_only_for_ticked_channels():
    cfg = config.from_dict(
        {"tv": {"url": "https://e.org/g.xml", "channels": ["51767", "54935"],
                "names": {"51767": "TF1", "54935": "France 2", "99999": "not ticked", "x": ""}}}
    )
    assert dict(cfg.tv_channel_names) == {"51767": "TF1", "54935": "France 2"}
    again = config.from_dict(config.to_dict(cfg))
    assert again.tv_channel_names == cfg.tv_channel_names


def test_no_names_means_nothing_written():
    assert "names" not in config.to_dict(Config())["tv"]
    assert config.from_dict({"tv": {"channels": ["a"], "names": "oops"}}).tv_channel_names == ()


def test_the_settings_page_gets_the_names_back_after_saving(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False, history_enabled=False)
    client = TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=("192.168.1.20", 5000))
    body = {
        "country": "FR", "language": "fr", "units": "metric", "theme": "france", "mode": "auto",
        "location": {"name": "Metz", "latitude": 49.1, "longitude": 6.17, "timezone": "Europe/Paris"},
        "tv": {"url": "https://e.org/g.xml", "channels": ["51767"], "names": {"51767": "TF1"}},
    }
    assert client.put("/api/admin/config", json=body).status_code == 200
    tv = client.get("/api/admin/config").json()["config"]["tv"]
    assert tv["channels"] == ["51767"] and tv["names"] == {"51767": "TF1"}
