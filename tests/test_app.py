import json
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import respx
from fastapi.testclient import TestClient

from beranda.app import create_app
from beranda.config import Config
from beranda.providers import weather
from tests.test_calendar_ics import SAMPLE
from tests.test_weather import payload

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=ZoneInfo("Europe/Paris"))


def make(tmp_path, **kw) -> TestClient:
    kw.setdefault("news_enabled", False)  # news has its own tests below
    kw.setdefault("history_enabled", False)  # history has its own tests below
    cfg = replace(Config(), cache_dir=tmp_path / "cache", **kw)
    return TestClient(create_app(cfg, now_fn=lambda: NOW))


def test_health_and_index(tmp_path):
    client = make(tmp_path, demo=True)
    assert client.get("/api/health").json()["status"] == "ok"
    page = client.get("/")
    assert page.status_code == 200 and "Beranda" in page.text


def test_security_headers_lock_down_the_page(tmp_path):
    response = make(tmp_path, demo=True).get("/")
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "unsafe-inline" not in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_demo_state_is_complete(tmp_path):
    state = make(tmp_path, demo=True).get("/api/state").json()
    assert state["demo"] is True and state["weather"]["source"] == "demo"
    assert state["mode"] == "light"  # noon in Paris
    assert state["season"]["kanji"] == "鴻雁来"
    assert state["sky"]["moon"]["name"] in {"new", "waning_crescent"}
    assert state["events"] and state["special_days"]
    assert state["errors"] == {} and state["stale"] == []
    assert state["window"] == {"start": "2026-10-01", "end": "2026-11-30"}


def test_fixed_mode_overrides_the_sun(tmp_path):
    assert make(tmp_path, demo=True, mode="night").get("/api/state").json()["mode"] == "night"


@respx.mock
def test_live_weather_is_fetched_once_then_cached(tmp_path):
    route = respx.get(weather.URL).mock(return_value=httpx.Response(200, json=payload()))
    client = make(tmp_path)
    first = client.get("/api/state").json()
    second = client.get("/api/state").json()
    assert first["weather"]["current"]["temp"] == 11 and second["weather"] == first["weather"]
    assert route.call_count == 1


@respx.mock
def test_a_broken_weather_source_does_not_blank_the_screen(tmp_path):
    respx.get(weather.URL).mock(return_value=httpx.Response(500))
    response = make(tmp_path).get("/api/state")
    state = response.json()
    assert response.status_code == 200
    assert state["weather"] is None and state["errors"]["weather"] == "HTTPStatusError"
    assert state["season"]["number"] == 49 and state["sky"]["moon"]  # local data still there


@respx.mock
def test_stale_weather_is_served_when_the_network_drops(tmp_path, monkeypatch):
    client = make(tmp_path)
    respx.get(weather.URL).mock(return_value=httpx.Response(200, json=payload()))
    assert client.get("/api/state").json()["weather"]["current"]["temp"] == 11

    monkeypatch.setattr("beranda.app.WEATHER_TTL", 0)  # force a refetch
    respx.get(weather.URL).mock(side_effect=httpx.ConnectError("wifi is down"))
    state = client.get("/api/state").json()
    assert state["weather"]["current"]["temp"] == 11
    assert state["stale"] == ["weather"] and state["errors"] == {}


@respx.mock
def test_ics_events_flow_through_and_the_secret_url_never_leaks(tmp_path):
    secret = "https://calendar.example.org/private/SECRET-TOKEN-123/basic.ics"
    respx.get(secret).mock(return_value=httpx.Response(200, text=SAMPLE))
    respx.get(weather.URL).mock(return_value=httpx.Response(500))
    good = make(tmp_path, ics_urls=(secret,)).get("/api/state").json()
    assert {e["title"] for e in good["events"]} >= {"Dentiste", "Week-end", "Yoga"}

    respx.get(secret).mock(side_effect=httpx.ConnectError(f"cannot reach {secret}"))
    bad = make(tmp_path / "other", ics_urls=(secret,)).get("/api/state")
    assert bad.status_code == 200
    assert "SECRET-TOKEN-123" not in json.dumps(bad.json())
    assert bad.json()["errors"]["calendar:0"] == "ConnectError"


def test_photos_are_listed_and_served_from_their_own_folder(tmp_path):
    folder = tmp_path / "pictures"
    folder.mkdir()
    (folder / "beach.jpg").write_bytes(b"fake-jpeg-bytes")
    client = make(tmp_path, demo=True, photos_folder=str(folder), photos_interval=7)

    state = client.get("/api/state").json()
    assert state["photos"] == {"names": ["beach.jpg"], "interval": 7}

    served = client.get("/api/photos/beach.jpg")
    assert served.status_code == 200 and served.content == b"fake-jpeg-bytes"

    assert client.get("/api/photos/../config.toml").status_code == 404
    assert client.get("/api/photos/missing.jpg").status_code == 404


def test_no_photos_folder_means_an_empty_carousel(tmp_path):
    state = make(tmp_path, demo=True).get("/api/state").json()
    assert state["photos"] == {"names": [], "interval": 20}


def test_state_reports_nothing_playing_by_default(tmp_path):
    state = make(tmp_path, demo=True).get("/api/state").json()
    assert state["radio"] == {"playing": False, "station": None, "volume": 70}


def test_no_tv_guide_configured_means_no_tv_section(tmp_path):
    state = make(tmp_path, demo=True).get("/api/state").json()
    assert state["tv"] is None


@respx.mock
def test_tv_prime_time_is_fetched_and_shown_in_local_time(tmp_path):
    guide = "https://example.org/guide.xml"
    xml = (
        b'<tv><channel id="c1"><display-name>France 2</display-name></channel>'
        b'<programme start="20261008190000 +0100" stop="20261008210000 +0100" channel="c1">'
        b"<title>Journal</title></programme></tv>"
    )
    respx.get(guide).mock(return_value=httpx.Response(200, content=xml))
    client = make(
        tmp_path, demo=True, tv_xmltv_url=guide, tv_channels=("c1",),
        tv_prime_start="18:00", tv_prime_end="22:00",
    )
    state = client.get("/api/state").json()
    # The feed says +0100, but Paris is on summer time (+0200) in October, so local time shifts by an hour.
    assert state["tv"] == {
        "programmes": [{"channel": "France 2", "title": "Journal", "start": "20:00", "stop": "22:00"}]
    }


@respx.mock
def test_a_broken_tv_guide_does_not_blank_the_screen(tmp_path):
    guide = "https://example.org/guide.xml"
    respx.get(guide).mock(side_effect=httpx.ConnectError("down"))
    client = make(tmp_path, demo=True, tv_xmltv_url=guide, tv_channels=("c1",))
    state = client.get("/api/state").json()
    assert state["tv"] is None
    assert state["errors"]["tv"] == "ConnectError"


def test_history_disabled_by_default_in_these_tests(tmp_path):
    state = make(tmp_path).get("/api/state").json()
    assert state["history"] == []


@respx.mock
def test_history_is_fetched_for_the_configured_country(tmp_path):
    from beranda.providers import history

    respx.get(history.SPARQL_URL).mock(
        side_effect=[
            httpx.Response(
                200, json={"results": {"bindings": [{"c": {"value": "http://www.wikidata.org/entity/Q142"}}]}}
            ),
            httpx.Response(
                200,
                json={
                    "results": {
                        "bindings": [
                            {"eventLabel": {"value": "Bastille Day"}, "date": {"value": "1789-07-14T00:00:00Z"}}
                        ]
                    }
                },
            ),
        ]
    )
    client = make(tmp_path, history_enabled=True, country="FR")
    state = client.get("/api/state").json()
    assert state["history"] == [{"year": 1789, "label": "Bastille Day"}]


@respx.mock
def test_a_broken_history_source_does_not_blank_the_screen(tmp_path):
    from beranda.providers import history

    respx.get(history.SPARQL_URL).mock(side_effect=httpx.ConnectError("down"))
    client = make(tmp_path, history_enabled=True)
    state = client.get("/api/state").json()
    assert state["history"] == []
    assert state["errors"]["history"] == "ConnectError"
