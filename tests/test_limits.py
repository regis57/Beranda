from dataclasses import replace
from itertools import pairwise

import pytest
from fastapi.testclient import TestClient

from beranda import config, limits
from beranda.app import create_app
from beranda.config import Config

LOCAL = ("192.168.1.20", 5000)


@pytest.mark.parametrize(
    ("model", "ram", "expected"),
    [
        ("Raspberry Pi 2 Model B Rev 1.1", 1, "lite"),
        ("Raspberry Pi Zero 2 W Rev 1.0", 1, "lite"),
        ("Raspberry Pi 3 Model B Plus Rev 1.3", 1, "standard"),
        ("Raspberry Pi 4 Model B Rev 1.1", 1, "standard"),
        ("Raspberry Pi 4 Model B Rev 1.4", 2, "comfort"),
        ("Raspberry Pi 4 Model B Rev 1.5", 4, "plus"),
        ("Raspberry Pi 4 Model B Rev 1.4", 8, "max"),
        ("Raspberry Pi 5 Model B Rev 1.0", 2, "comfort"),
        ("Raspberry Pi 5 Model B Rev 1.0", 4, "plus"),
        ("Raspberry Pi 5 Model B Rev 1.0", 16, "max"),
        ("Raspberry Pi 400 Rev 1.0", 4, "plus"),
        ("", 16, "max"),  # not a Raspberry Pi: judged by its memory
        ("", 2, "comfort"),
    ],
)
def test_the_profile_follows_the_board_and_its_memory(model, ram, expected):
    assert limits.classify(model, ram) == expected


def test_bigger_profiles_never_allow_less():
    rows = [limits.for_profile(p) for p in limits.PROFILES]
    for smaller, bigger in pairwise(rows):
        assert all(getattr(bigger, f) > getattr(smaller, f) for f in vars(smaller) if f != "profile")


def test_the_choice_in_the_config_file_beats_the_detection(monkeypatch):
    assert limits.resolve("plus").profile == "plus"
    assert limits.resolve("auto").profile == "standard"  # BERANDA_PROFILE from conftest
    assert config.from_dict({"limits": {"profile": "max"}}).limits.profile == "max"
    with pytest.raises(ValueError, match="limits profile"):
        config.from_dict({"limits": {"profile": "huge"}})


def test_a_file_edited_by_hand_is_cut_to_the_limit_instead_of_overloading_the_pi():
    cap = limits.for_profile("standard")
    cfg = config.from_dict(
        {
            "calendar": {"ics_urls": [f"https://e.org/{i}.ics" for i in range(30)]},
            "tv": {"channels": [f"c{i}" for i in range(99)]},
            "news": {"sources": ["bbc"] * 30, "feeds": [f"https://e.org/{i}.xml" for i in range(5)]},
        }
    )
    assert len(cfg.ics_urls) == cap.calendars and len(cfg.tv_channels) == cap.tv_channels
    assert len(cfg.news_sources) + len(cfg.news_feeds) == cap.news_sources  # media and feeds share one limit


def test_a_chosen_profile_is_written_back_only_when_not_automatic():
    assert "limits" not in config.to_dict(Config())
    assert config.to_dict(replace(Config(), limits_profile="plus"))["limits"] == {"profile": "plus"}


def _client(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False, history_enabled=False)
    return TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=LOCAL)


def _body(**over):
    body = {
        "country": "FR", "language": "fr", "units": "metric", "theme": "france", "mode": "auto",
        "location": {"name": "Metz", "latitude": 49.1, "longitude": 6.17, "timezone": "Europe/Paris"},
    }
    body.update(over)
    return body


def test_the_settings_page_refuses_too_many_things_with_a_clear_sentence(tmp_path):
    client = _client(tmp_path)
    too_many = {"ics_urls": [f"https://e.org/{i}.ics" for i in range(11)]}
    r = client.put("/api/admin/config", json=_body(calendar=too_many))
    assert r.status_code == 422 and "too many calendars: 11" in r.json()["detail"]
    ok = {"ics_urls": [f"https://e.org/{i}.ics" for i in range(10)]}
    assert client.put("/api/admin/config", json=_body(calendar=ok)).status_code == 200


def test_the_settings_page_tells_the_limits_and_the_device(tmp_path):
    data = _client(tmp_path).get("/api/admin/config").json()["limits"]
    assert data["profile"] == "standard" and data["calendars"] == 10 and "device" in data


def test_the_photo_frame_stops_taking_pictures_when_full(tmp_path, monkeypatch):
    monkeypatch.setenv("BERANDA_PROFILE", "lite")
    client = _client(tmp_path)
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    room = limits.for_profile("lite").photos
    folder = tmp_path / "beranda-photos"
    folder.mkdir()
    for i in range(room):
        (folder / f"p{i}.png").write_bytes(png)
    r = client.post("/api/admin/photos?name=one-more.png", content=png)
    assert r.status_code == 409 and str(room) in r.json()["detail"]
