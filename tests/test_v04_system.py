import subprocess
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from beranda import config, system
from beranda.app import create_app
from beranda.config import Config

ROOT = Path(__file__).parent.parent
LOCAL = ("192.168.1.20", 5000)
PARIS = ZoneInfo("Europe/Paris")


def at(hh: int, mm: int = 0) -> datetime:
    return datetime(2026, 10, 9, hh, mm, tzinfo=PARIS)


def test_screen_hours_across_midnight():
    cfg = replace(Config(), screen_off="23:00", screen_on="06:30")
    assert system.screen_should_be_on(cfg, at(22, 59))
    assert not system.screen_should_be_on(cfg, at(23, 0))
    assert not system.screen_should_be_on(cfg, at(3))
    assert system.screen_should_be_on(cfg, at(6, 30))


def test_screen_hours_within_a_day_and_disabled():
    cfg = replace(Config(), screen_off="01:00", screen_on="06:00")
    assert not system.screen_should_be_on(cfg, at(2)) and system.screen_should_be_on(cfg, at(12))
    assert system.screen_should_be_on(Config(), at(3))  # nothing set: always on


def test_screen_settings_are_validated_and_saved():
    cfg = config.from_dict({"screen": {"rotate": 90, "off": "23:00", "on": "6:30"}})
    assert (cfg.screen_rotate, cfg.screen_off, cfg.screen_on) == (90, "23:00", "06:30")
    assert config.to_dict(cfg)["screen"] == {"rotate": 90, "off": "23:00", "on": "06:30"}
    with pytest.raises(ValueError):
        config.from_dict({"screen": {"rotate": 45}})
    with pytest.raises(ValueError):
        config.from_dict({"screen": {"off": "25:00"}})


def test_kiosk_endpoint_and_dark_page_at_night(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path, demo=True, news_enabled=False,
                  screen_rotate=270, screen_off="23:00", screen_on="06:30")
    client = TestClient(create_app(cfg, now_fn=lambda: at(23, 30)))
    assert client.get("/api/screen").json() == {"on": False, "rotate": 270}
    assert client.get("/api/state").json()["sleep"] is True


def test_first_start_shows_where_to_set_up(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False)
    path = tmp_path / "config.toml"
    client = TestClient(create_app(cfg, config_path=path), client=LOCAL)
    setup = client.get("/api/state").json()["setup"]
    assert setup["needed"] is True and all(u.endswith("/admin") for u in setup["urls"])
    svg = client.get("/api/setup-qr.svg")
    assert svg.status_code == 200 and svg.text.startswith("<svg")
    path.write_text('country = "FR"\n')  # once saved, the card goes away
    assert client.get("/api/state").json()["setup"]["needed"] is False


def test_demo_never_shows_the_setup_card(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path, demo=True, news_enabled=False)
    client = TestClient(create_app(cfg, config_path=tmp_path / "none.toml"))
    assert client.get("/api/state").json()["setup"]["needed"] is False


def _installed(tmp_path, monkeypatch):
    requests = tmp_path / "requests"
    requests.mkdir()
    info = tmp_path / "install.env"
    info.write_text("# comment\nPREFIX=/opt/beranda\nBRANCH=main\nSCREEN=1\nCOMMIT=abc1234\n")
    monkeypatch.setenv("BERANDA_REQUESTS", str(requests))
    monkeypatch.setenv("BERANDA_INSTALL_INFO", str(info))
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False)
    return TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=LOCAL), requests


def test_system_info_and_requests(tmp_path, monkeypatch):
    client, requests = _installed(tmp_path, monkeypatch)
    info = client.get("/api/admin/system").json()
    assert info["installed"] and info["actions"] and info["commit"] == "abc1234" and info["screen"]
    assert client.post("/api/admin/system/restart-screen").json() == {"requested": "restart-screen"}
    assert (requests / "restart-screen").exists()
    assert client.post("/api/admin/system/reset").json() == {"requested": "reset"}
    assert (requests / "reset").exists()
    assert client.post("/api/admin/system/rm").status_code == 404
    assert not (requests / "rm").exists()


def test_system_requests_need_the_installer(tmp_path, monkeypatch):
    monkeypatch.delenv("BERANDA_REQUESTS", raising=False)
    monkeypatch.setenv("BERANDA_INSTALL_INFO", str(tmp_path / "missing.env"))
    cfg = replace(Config(), cache_dir=tmp_path, news_enabled=False)
    client = TestClient(create_app(cfg, config_path=tmp_path / "c.toml"), client=LOCAL)
    assert client.get("/api/admin/system").json()["installed"] is False
    assert client.post("/api/admin/system/update").status_code == 409


def test_system_requests_are_refused_from_outside(tmp_path, monkeypatch):
    _installed(tmp_path, monkeypatch)
    cfg = replace(Config(), cache_dir=tmp_path / "c2", news_enabled=False)
    outside = TestClient(create_app(cfg, config_path=tmp_path / "x.toml"), client=("8.8.8.8", 1))
    assert outside.post("/api/admin/system/reboot").status_code == 403


@respx.mock
def test_update_check(tmp_path, monkeypatch):
    client, _ = _installed(tmp_path, monkeypatch)
    route = respx.get(system.RAW_VERSION_URL.format(branch="main"))
    route.mock(return_value=httpx.Response(200, text='__version__ = "9.9.0"\n'))
    assert client.get("/api/admin/system/latest").json() == {"latest": "9.9.0", "update_available": True}
    route.mock(return_value=httpx.Response(200, text='__version__ = "0.0.1"\n'))
    assert client.get("/api/admin/system/latest").json()["update_available"] is False
    route.mock(side_effect=httpx.ConnectError("offline"))
    assert client.get("/api/admin/system/latest").json() == {"latest": None, "update_available": False}


def test_installer_dry_run_lists_every_step():
    out = subprocess.run(["bash", str(ROOT / "install.sh"), "--dry-run", "--hostname", "mirror"],
                         capture_output=True, text=True, check=True).stdout
    for expected in ("apt-get install", "cage", "Creating the 'beranda' user", "venv/bin/pip install",
                     "beranda-kiosk.service", "systemctl enable --now beranda.service",
                     "hostnamectl set-hostname mirror", "http://"):
        assert expected in out, expected
    no_screen = subprocess.run(["bash", str(ROOT / "install.sh"), "--dry-run", "--no-screen"],
                               capture_output=True, text=True, check=True).stdout
    apt_line = next(line for line in no_screen.splitlines() if "apt-get install" in line)
    assert "cage" not in apt_line and "chromium" not in apt_line
    assert "enable beranda-kiosk" not in no_screen


def test_installer_refuses_bad_names():
    bad = subprocess.run(["bash", str(ROOT / "install.sh"), "--dry-run", "--hostname", "My Mirror!"],
                         capture_output=True, text=True, check=False)
    assert bad.returncode != 0 and "lowercase" in bad.stderr


def test_unit_templates_only_use_known_placeholders():
    import re

    for unit in (ROOT / "system").glob("*.in"):
        assert set(re.findall(r"@(\w+)@", unit.read_text())) <= {"PREFIX", "USER", "CONFDIR", "STATEDIR"}, unit
