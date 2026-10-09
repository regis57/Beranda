import tomllib
from dataclasses import replace

import httpx
import respx
from fastapi.testclient import TestClient

from beranda import admin, config
from beranda.app import create_app
from beranda.config import Config
from tests.test_calendar_ics import SAMPLE

LOCAL = ("192.168.1.20", 5000)
OUTSIDE = ("8.8.8.8", 5000)


def make(tmp_path, client=LOCAL, **kw):
    kw.setdefault("news_enabled", False)
    kw.setdefault("history_enabled", False)
    cfg = replace(Config(), cache_dir=tmp_path / "cache", **kw)
    path = tmp_path / "config.toml"
    return TestClient(create_app(cfg, config_path=path), client=client), path


def valid_body(**over):
    body = {
        "country": "ID", "language": "id", "units": "metric", "theme": "indonesia", "mode": "auto",
        "location": {"name": "Yogyakarta", "latitude": -7.797, "longitude": 110.37, "timezone": "Asia/Jakarta"},
        "calendar": {"ics_urls": ["https://example.org/a.ics"]},
        "key_dates": [{"date": "2018-06-02", "label": "Ayu", "kind": "birth"}],
    }
    body.update(over)
    return body


def test_admin_page_and_options_are_served(tmp_path):
    client, _ = make(tmp_path)
    assert client.get("/admin").status_code == 200
    data = client.get("/api/admin/config").json()
    assert data["editable"] is True and "FR" in data["options"]["countries"]
    assert data["options"]["themes"][:3] == ["japan", "indonesia", "france"]
    assert {"germany", "spain", "italy", "portugal", "brazil"} <= set(data["options"]["themes"])
    # one entry per country: no three-letter duplicates (FRA) nor aliases (UK)
    codes = data["options"]["countries"]
    assert all(len(c) == 2 for c in codes) and "UK" not in codes and "GB" in codes
    assert "server" not in data["config"] and "admin" not in data["config"]


def test_outside_addresses_are_refused(tmp_path):
    client, _ = make(tmp_path, client=OUTSIDE)
    assert client.get("/api/admin/config").status_code == 403
    assert client.get("/api/admin/status").status_code == 403
    assert client.put("/api/admin/config", json=valid_body()).status_code == 403
    # the display itself stays reachable
    assert client.get("/api/state").status_code == 200


def test_loopback_and_ipv4_mapped_ipv6_count_as_local():
    assert admin._is_local("127.0.0.1") and admin._is_local("::1")
    assert admin._is_local("::ffff:192.168.0.5") and admin._is_local("10.0.0.2")
    assert not admin._is_local("8.8.8.8") and not admin._is_local("testclient")
    assert not admin._is_local(None) and not admin._is_local("")


def test_saving_writes_a_private_toml_and_applies_it_live(tmp_path):
    client, path = make(tmp_path)
    assert client.put("/api/admin/config", json=valid_body()).json()["saved"] is True
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    written = tomllib.loads(path.read_text())
    assert written["location"]["name"] == "Yogyakarta" and written["theme"] == "indonesia"
    assert written["key_dates"] == [{"date": "2018-06-02", "label": "Ayu", "kind": "birth"}]
    # the written file loads back to the same configuration
    assert config.load(path).location.timezone == "Asia/Jakarta"
    # and the running display uses it without a restart
    state = client.get("/api/state").json()
    assert state["config"]["location"]["name"] == "Yogyakarta"
    assert state["season"]["kind"] == "mangsa"


def test_invalid_settings_are_rejected_and_nothing_is_written(tmp_path):
    client, path = make(tmp_path)
    bad = valid_body(location={"name": "X", "latitude": 123, "longitude": 0, "timezone": "UTC"})
    assert client.put("/api/admin/config", json=bad).status_code == 422
    assert client.put("/api/admin/config", json=valid_body(units="furlongs")).status_code == 422
    bad_key = valid_body(key_dates=[{"date": "tomorrow", "label": "x", "kind": "other"}])
    assert client.put("/api/admin/config", json=bad_key).status_code == 422
    assert not path.exists()


def test_cross_origin_writes_are_refused(tmp_path):
    client, path = make(tmp_path)
    r = client.put("/api/admin/config", json=valid_body(), headers={"origin": "https://evil.example"})
    assert r.status_code == 403 and not path.exists()
    ok = client.put("/api/admin/config", json=valid_body(), headers={"origin": "http://testserver"})
    assert ok.status_code == 200


def test_pin_is_required_when_set_and_can_be_set_from_the_page(tmp_path):
    client, _ = make(tmp_path)
    assert client.get("/api/admin/status").json()["pin_required"] is False
    assert client.put("/api/admin/config", json=valid_body(pin="2468")).status_code == 200
    assert client.get("/api/admin/status").json()["pin_required"] is True
    assert client.get("/api/admin/config").status_code == 401
    assert client.get("/api/admin/config", headers={"x-beranda-pin": "0000"}).status_code == 401
    good = {"x-beranda-pin": "2468"}
    assert client.get("/api/admin/config", headers=good).json()["pin_set"] is True
    # saving again without a pin key keeps the pin
    assert client.put("/api/admin/config", json=valid_body(), headers=good).status_code == 200
    assert client.get("/api/admin/config").status_code == 401
    # an empty pin clears it
    assert client.put("/api/admin/config", json=valid_body(pin=""), headers=good).status_code == 200
    assert client.get("/api/admin/config").status_code == 200


def test_without_a_config_path_saving_is_refused(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "cache")
    client = TestClient(create_app(cfg), client=LOCAL)
    assert client.get("/api/admin/config").json()["editable"] is False
    assert client.put("/api/admin/config", json=valid_body()).status_code == 409


def test_state_can_preview_another_theme(tmp_path):
    client, _ = make(tmp_path, demo=True)
    assert client.get("/api/state?theme=france").json()["season"]["kind"] == "republican"
    assert client.get("/api/state?theme=../../x").json()["season"]["kind"] == "ko"


@respx.mock
def test_city_search_proxies_open_meteo(tmp_path):
    respx.get(admin.GEOCODE_URL).mock(return_value=httpx.Response(200, json={"results": [
        {"name": "Yogyakarta", "admin1": "Special Region", "country_code": "ID",
         "latitude": -7.8, "longitude": 110.36, "timezone": "Asia/Jakarta", "population": 1}]}))
    client, _ = make(tmp_path)
    found = client.get("/api/admin/geocode", params={"q": "Yogya", "language": "id"}).json()["results"]
    assert found == [{"name": "Yogyakarta", "region": "Special Region", "country": "ID",
                      "latitude": -7.8, "longitude": 110.36, "timezone": "Asia/Jakarta"}]


@respx.mock
def test_city_search_failure_is_a_clean_502(tmp_path):
    respx.get(admin.GEOCODE_URL).mock(side_effect=httpx.ConnectError("down"))
    client, _ = make(tmp_path)
    assert client.get("/api/admin/geocode", params={"q": "Paris"}).status_code == 502


@respx.mock
def test_ics_test_reports_events_and_never_echoes_the_secret(tmp_path):
    secret = "https://calendar.example.org/private/SECRET-TOKEN-9/basic.ics"
    client, _ = make(tmp_path)
    respx.get(secret).mock(return_value=httpx.Response(200, text=SAMPLE))
    ok = client.post("/api/admin/test-ics", json={"url": secret}).json()
    assert ok["ok"] is True
    respx.get(secret).mock(side_effect=httpx.ConnectError(f"cannot reach {secret}"))
    bad = client.post("/api/admin/test-ics", json={"url": secret}).json()
    assert bad == {"ok": False, "error": "ConnectError"}


def test_photos_count_gives_live_feedback_while_typing(tmp_path):
    folder = tmp_path / "pics"
    folder.mkdir()
    (folder / "a.jpg").write_bytes(b"x")
    (folder / "b.png").write_bytes(b"x")
    client, _ = make(tmp_path)
    assert client.get("/api/admin/photos-count", params={"folder": str(folder)}).json() == {"count": 2}
    assert client.get("/api/admin/photos-count", params={"folder": str(tmp_path / "nope")}).json() == {"count": 0}


def test_photos_settings_round_trip(tmp_path):
    client, path = make(tmp_path)
    body = valid_body(photos={"folder": "/home/pi/pictures", "interval": 30})
    assert client.put("/api/admin/config", json=body).json() == {"saved": True, "path": str(path)}
    saved = tomllib.loads(path.read_text())
    assert saved["photos"] == {"folder": "/home/pi/pictures", "interval": 30}


@respx.mock
def test_radio_search_proxies_radio_browser(tmp_path):
    from beranda.providers import radio

    respx.get(f"{radio.MIRRORS[0]}/json/stations/search").mock(
        return_value=httpx.Response(200, json=[{"stationuuid": "u1", "name": "Test", "url": "http://s/live"}])
    )
    client, _ = make(tmp_path)
    found = client.get("/api/admin/radio-search", params={"name": "test"}).json()
    assert found["stations"][0]["uuid"] == "u1"


@respx.mock
def test_radio_search_failure_is_a_clean_502(tmp_path):
    from beranda.providers import radio

    for mirror in radio.MIRRORS:
        respx.get(f"{mirror}/json/stations/search").mock(side_effect=httpx.ConnectError("down"))
    client, _ = make(tmp_path)
    assert client.get("/api/admin/radio-search").status_code == 502


def test_radio_play_stop_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpv")
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: _FakeProc())
    client, _ = make(tmp_path)

    station = {"uuid": "u1", "name": "Test FM", "url": "http://s/live"}
    played = client.post("/api/admin/radio-play", json=station).json()
    assert played == {"playing": True, "station": station, "volume": 70}
    assert client.get("/api/admin/radio-status").json()["playing"] is True

    stopped = client.post("/api/admin/radio-stop").json()
    assert stopped == {"playing": False, "station": None, "volume": 70}


def test_radio_play_without_mpv_is_a_clean_409(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    client, _ = make(tmp_path)
    r = client.post("/api/admin/radio-play", json={"uuid": "u1", "name": "Test", "url": "http://s/live"})
    assert r.status_code == 409


def test_radio_settings_round_trip(tmp_path):
    client, path = make(tmp_path)
    station = {"uuid": "u1", "name": "Test FM", "url": "http://s/live", "favicon": "", "country": "FR"}
    body = valid_body(radio={"stations": [station], "volume": 45})
    assert client.put("/api/admin/config", json=body).json()["saved"] is True
    saved = tomllib.loads(path.read_text())
    assert saved["radio"] == {"stations": [station], "volume": 45}


@respx.mock
def test_tv_test_lists_channels_for_the_picker(tmp_path):
    guide = "https://example.org/guide.xml"
    respx.get(guide).mock(
        return_value=httpx.Response(
            200, content=b'<tv><channel id="c1"><display-name>France 2</display-name></channel></tv>'
        )
    )
    client, _ = make(tmp_path)
    found = client.post("/api/admin/test-tv", json={"url": guide}).json()
    assert found == {"ok": True, "channels": [{"id": "c1", "name": "France 2"}]}


@respx.mock
def test_tv_test_failure_is_reported_without_a_stack_trace(tmp_path):
    guide = "https://example.org/guide.xml"
    respx.get(guide).mock(side_effect=httpx.ConnectError("down"))
    client, _ = make(tmp_path)
    assert client.post("/api/admin/test-tv", json={"url": guide}).json() == {"ok": False, "error": "ConnectError"}


def test_tv_settings_round_trip(tmp_path):
    client, path = make(tmp_path)
    body = valid_body(
        tv={"url": "https://example.org/guide.xml", "channels": ["c1"], "prime_start": "19:00", "prime_end": "22:00"}
    )
    assert client.put("/api/admin/config", json=body).json()["saved"] is True
    saved = tomllib.loads(path.read_text())
    assert saved["tv"] == {
        "url": "https://example.org/guide.xml", "channels": ["c1"], "prime_start": "19:00", "prime_end": "22:00"
    }


def test_voice_settings_round_trip(tmp_path):
    client, path = make(tmp_path)
    body = valid_body(voice={"enabled": True, "wake_word": "alexa"})
    assert client.put("/api/admin/config", json=body).json()["saved"] is True
    saved = tomllib.loads(path.read_text())
    assert saved["voice"] == {"enabled": True, "wake_word": "alexa"}


def test_history_settings_round_trip(tmp_path):
    client, path = make(tmp_path)
    body = valid_body(history={"enabled": False})
    assert client.put("/api/admin/config", json=body).json()["saved"] is True
    saved = tomllib.loads(path.read_text())
    assert saved["history"] == {"enabled": False}


class _FakeProc:
    def __init__(self):
        self.alive = True

    def poll(self):
        return None if self.alive else 0

    def terminate(self):
        self.alive = False

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.alive = False
