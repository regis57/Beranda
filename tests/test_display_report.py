from dataclasses import replace

from fastapi.testclient import TestClient

from beranda.app import create_app
from beranda.config import Config

EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36 Edg/154.0.0.0"


def test_what_the_screen_reports_ends_up_in_the_diagnostic_file(tmp_path):
    app = create_app(replace(Config(), cache_dir=tmp_path / "c", demo=True), config_path=tmp_path / "c.toml")
    screen = TestClient(app, client=("192.168.1.30", 5000))
    r = screen.post("/api/report", json={"event": "microphone: network (secure page: true, https:)"}, headers={"User-Agent": EDGE})
    assert r.status_code == 200
    text = TestClient(app, client=("192.168.1.20", 5000)).post("/api/admin/diagnostics", json={}).text
    assert "microphone: network" in text and "Edge 154 on Windows" in text


def test_reports_come_from_the_home_network_only(tmp_path):
    app = create_app(replace(Config(), cache_dir=tmp_path / "c", demo=True), config_path=tmp_path / "c.toml")
    assert TestClient(app, client=("8.8.8.8", 5000)).post("/api/report", json={"event": "x"}).status_code == 403
