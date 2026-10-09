"""The "Advanced user" card of the settings page: changing the port, and the safety net."""

import asyncio
import os
import socket
import tomllib
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from beranda import __main__ as entry
from beranda import config, system
from beranda.app import create_app
from beranda.config import Config

LOCAL = ("192.168.1.20", 5000)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def busy_port():
    """A port some other program is listening on."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        yield s.getsockname()[1]


def _client(tmp_path):
    cfg = replace(Config(), host="127.0.0.1", cache_dir=tmp_path / "c", news_enabled=False, history_enabled=False)
    path = tmp_path / "config.toml"
    return TestClient(create_app(cfg, config_path=path), client=LOCAL), path


def test_a_port_must_be_a_free_number_from_1024_up(busy_port):
    assert system.port_problem(80, 8080, "127.0.0.1") == "range"  # below 1024 needs root
    assert system.port_problem(70000, 8080, "127.0.0.1") == "range"
    assert system.port_problem("8081", 8080, "127.0.0.1") == "range"
    assert system.port_problem(True, 8080, "127.0.0.1") == "range"
    assert system.port_problem(8080, 8080, "127.0.0.1") == "same"
    assert system.port_problem(busy_port, 8080, "127.0.0.1") == "busy"
    assert system.port_problem(free_port(), 8080, "127.0.0.1") is None


def test_the_settings_page_tells_the_port_in_use(tmp_path):
    client, _ = _client(tmp_path)
    assert client.get("/api/admin/system").json()["port"] == 8080


def test_changing_the_port_needs_a_confirmation_and_a_free_number(tmp_path, busy_port):
    client, path = _client(tmp_path)
    port = free_port()
    assert client.post("/api/admin/system/port", json={"port": port}).status_code == 400
    r = client.post("/api/admin/system/port", json={"port": busy_port, "confirmed": True})
    assert r.status_code == 422 and r.json()["detail"] == "port_busy"
    r = client.post("/api/admin/system/port", json={"port": 80, "confirmed": True})
    assert r.status_code == 422 and r.json()["detail"] == "port_range"
    r = client.post("/api/admin/system/port", json={"port": 8080, "confirmed": True})
    assert r.status_code == 422 and r.json()["detail"] == "port_same"
    assert not path.exists()  # nothing was written for any of those


def test_the_new_port_is_saved_and_survives_the_next_save(tmp_path, monkeypatch):
    monkeypatch.setattr(system, "restart_server_soon", lambda: True)
    client, path = _client(tmp_path)
    port = free_port()
    r = client.post("/api/admin/system/port", json={"port": port, "confirmed": True})
    assert r.status_code == 200 and r.json() == {"port": port, "restarting": True, "screen": False}
    assert tomllib.loads(path.read_text())["server"]["port"] == port
    info = client.get("/api/admin/system").json()
    assert info["saved_port"] == port and info["port"] == 8080  # it only applies after the restart
    # saving the other settings afterwards must not bring the old port back
    body = {
        "country": "FR", "language": "fr", "units": "metric", "theme": "france", "mode": "auto",
        "location": {"name": "Metz", "latitude": 49.1, "longitude": 6.17, "timezone": "Europe/Paris"},
    }
    assert client.put("/api/admin/config", json=body).status_code == 200
    assert tomllib.loads(path.read_text())["server"]["port"] == port


def test_the_screen_on_the_pi_is_restarted_so_it_opens_the_new_address(tmp_path, monkeypatch):
    asked = []
    monkeypatch.setattr(system, "restart_server_soon", lambda: True)
    monkeypatch.setattr(system, "install_info", lambda: {"SCREEN": "1"})
    monkeypatch.setattr(system, "request_action", asked.append)
    client, _ = _client(tmp_path)
    r = client.post("/api/admin/system/port", json={"port": free_port(), "confirmed": True})
    assert r.json()["screen"] is True and asked == ["restart-screen"]


def test_without_systemd_nothing_is_stopped_and_the_page_says_to_restart(tmp_path, monkeypatch):
    monkeypatch.delenv("INVOCATION_ID", raising=False)
    client, _ = _client(tmp_path)
    r = client.post("/api/admin/system/port", json={"port": free_port(), "confirmed": True})
    assert r.status_code == 200 and r.json()["restarting"] is False


def test_the_server_stops_itself_only_when_systemd_will_start_it_again(tmp_path, monkeypatch):
    info = tmp_path / "install.env"
    info.write_text("SCREEN=0\n")
    monkeypatch.setenv("BERANDA_INSTALL_INFO", str(info))
    killed = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append(sig))

    async def go():
        monkeypatch.delenv("INVOCATION_ID", raising=False)
        assert system.restart_server_soon(0.01) is False
        monkeypatch.setenv("INVOCATION_ID", "abc")
        assert system.restart_server_soon(0.01) is True
        await asyncio.sleep(0.1)

    asyncio.run(go())
    assert len(killed) == 1


def test_a_taken_port_sends_beranda_back_to_8080_instead_of_failing_forever(tmp_path, busy_port, monkeypatch):
    path = tmp_path / "config.toml"
    path.write_text(f'[server]\nhost = "127.0.0.1"\nport = {busy_port}\n')
    started = {}
    monkeypatch.setattr(entry.uvicorn, "run", lambda app, **kw: started.update(kw))
    entry.main(["--config", str(path)])
    assert started["port"] == system.DEFAULT_PORT
    assert tomllib.loads(path.read_text())["server"]["port"] == system.DEFAULT_PORT  # the screen reads it too
    assert config.load(path).port == system.DEFAULT_PORT
