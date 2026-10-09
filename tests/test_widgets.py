"""The optional extras: air / UV / pollen, official warnings, ephemeris, 24-hour graph."""

from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from beranda import config
from beranda.app import create_app
from beranda.config import Config
from beranda.providers import air, alerts, ephemeris, weather

NOW = datetime(2026, 10, 9, 21, 0, tzinfo=UTC)


# ---- air quality, UV, pollen ------------------------------------------------------------
def test_air_levels_use_the_european_scale_by_default():
    out = air.parse({"current": {"european_aqi": 34, "us_aqi": 90, "uv_index": 6.4, "grass_pollen": 28, "birch_pollen": 4, "olive_pollen": 0.2}})
    assert (out["aqi"], out["aqi_level"], out["aqi_scale"]) == (34, 1, "eu")  # 20-40 = fair
    assert (out["uv"], out["uv_level"]) == (6.4, 2)  # 6-8 = high
    assert [(p["kind"], p["level"]) for p in out["pollen"]] == [("grass", 2), ("birch", 1)]  # olive < 1 grain: left out


def test_air_uses_the_us_scale_for_the_united_states():
    out = air.parse({"current": {"european_aqi": 34, "us_aqi": 120}}, us_scale=True)
    assert (out["aqi"], out["aqi_level"], out["aqi_scale"]) == (120, 2, "us")


def test_air_with_missing_values_is_empty_not_a_crash():
    out = air.parse({})
    assert out["aqi"] is None and out["uv"] is None and out["pollen"] == []


# ---- weather warnings ---------------------------------------------------------------------
def entry(area, title, severity="Moderate", expires="2026-10-10T20:00:00+00:00", onset="2026-10-09T04:00:00+00:00", status="Actual"):
    return f"""<entry xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">
      <cap:areaDesc>{area}</cap:areaDesc><cap:event>{title}</cap:event><cap:severity>{severity}</cap:severity>
      <cap:onset>{onset}</cap:onset><cap:expires>{expires}</cap:expires><cap:status>{status}</cap:status>
      <title>{title}</title></entry>"""


def feed(*entries):
    return '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">' + "".join(entries) + "</feed>"


def test_warnings_for_my_area_are_found_ignoring_accents_and_case():
    xml = feed(
        entry("Drôme", "Yellow Thunderstorm Warning issued for France - Drôme"),
        entry("Moselle", "Orange Wind Warning issued for France - Moselle", severity="Severe"),
        entry("Moselle", "Yellow Wind Warning issued for France - Moselle"),
        entry("Var", "Red Rain Warning issued for France - Var", severity="Extreme"),
    )
    found = alerts.for_area(alerts.parse(xml, NOW), "moselle")
    assert [(w["kind"], w["level"]) for w in found] == [("wind", 2)]  # the worst wind warning only
    assert alerts.for_area(alerts.parse(xml, NOW), "DROME")[0]["kind"] == "thunderstorm"
    assert alerts.for_area(alerts.parse(xml, NOW), "") == []  # no area typed: nothing is guessed


def test_over_or_not_yet_started_or_test_warnings_are_ignored():
    xml = feed(
        entry("Moselle", "Yellow Wind Warning", expires="2026-10-09T10:00:00+00:00"),  # already over
        entry("Moselle", "Yellow Fog Warning", onset="2026-10-12T00:00:00+00:00"),  # in three days
        entry("Moselle", "Yellow Snow Warning", status="Exercise"),
        entry("Moselle", "Yellow Heat Warning issued for France - Moselle"),
    )
    assert [w["kind"] for w in alerts.parse(xml, NOW)] == ["heat"]


def test_event_text_becomes_a_short_kind():
    assert alerts._kind("Moderate thunderstorm warning") == "thunderstorm"
    assert alerts._kind("Rain-flood warning") == "flood"
    assert alerts._kind("High temperature warning") == "heat"
    assert alerts._kind("Something new") == "other"


def test_feed_countries():
    assert alerts.supported("fr") and alerts.supported("GB")
    assert not alerts.supported("JP")


# ---- ephemeris --------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload",
    [
        {"data": {"dates": {"day": 9, "month": 10}, "namedays": {"fr": "Denis", "de": "Dionys"}}},
        {"day": 9, "month": 10, "namedays": {"fr": "Denis"}},
    ],
)
def test_the_nameday_is_found_however_the_service_nests_it(payload):
    assert ephemeris.parse_nameday(payload, "FR") == "Denis"


def test_a_country_without_a_nameday_gives_nothing():
    assert ephemeris.parse_nameday({"data": {"namedays": {"fr": "Denis"}}}, "JP") is None
    assert not ephemeris.has_nameday("JP") and ephemeris.has_nameday("pl")


def test_daylight_is_shorter_every_day_in_october_in_the_north():
    out = ephemeris.daylight(datetime(2026, 10, 9, 12, tzinfo=UTC), 49.1, 6.2, "Europe/Paris")
    assert 600 < out["daylight_min"] < 720 and out["delta_s"] < 0


# ---- the 24-hour graph data ----------------------------------------------------------------
def test_hourly_starts_with_the_current_hour_and_has_24_entries():
    times = [f"2026-10-09T{h:02d}:00" for h in range(24)] + [f"2026-10-10T{h:02d}:00" for h in range(24)]
    payload = {"hourly": {"time": times, "temperature_2m": list(range(48)), "precipitation": [0.1] * 48, "wind_speed_10m": [12.4] * 48}}
    out = weather._hourly(payload, "2026-10-09T21:15")
    assert len(out) == 24 and out[0]["time"] == "2026-10-09T21:00" and out[0]["temp"] == 21
    assert weather._hourly({}, "2026-10-09T21:15") == []


# ---- config --------------------------------------------------------------------------------------
def test_widgets_defaults_and_round_trip():
    cfg = config.from_dict({})
    assert (cfg.widget_chart, cfg.widget_air, cfg.widget_alerts, cfg.widget_ephemeris, cfg.second_clock) == (True, True, False, True, "")
    cfg = config.from_dict({"widgets": {"alerts": True, "alerts_area": "  Moselle ", "second_clock": "Asia/Jakarta", "chart": False}})
    assert cfg.alerts_area == "Moselle" and cfg.second_clock == "Asia/Jakarta" and not cfg.widget_chart
    assert config.to_dict(cfg)["widgets"]["second_clock"] == "Asia/Jakarta"


def test_an_unknown_time_zone_is_refused():
    with pytest.raises(ValueError, match="time zone"):
        config.from_dict({"widgets": {"second_clock": "Mars/Olympus"}})


# ---- the state endpoint ----------------------------------------------------------------------------
def client(tmp_path, **kw):
    cfg = replace(Config(), cache_dir=tmp_path / "cache", news_enabled=False, history_enabled=False, **kw)
    return TestClient(create_app(cfg, now_fn=lambda: NOW))


@respx.mock
def test_state_carries_air_alerts_and_nameday_when_switched_on(tmp_path):
    respx.get(air.URL).mock(return_value=httpx.Response(200, json={"current": {"european_aqi": 10, "uv_index": 1.0}}))
    respx.get(alerts.FEED.format(slug="france")).mock(
        return_value=httpx.Response(200, text=feed(entry("Moselle", "Yellow Wind Warning issued for France - Moselle")))
    )
    respx.get(ephemeris.NAMEDAY_URL).mock(return_value=httpx.Response(200, json={"data": {"namedays": {"fr": "Denis"}}}))
    state = client(tmp_path, demo=True, widget_alerts=True, alerts_area="Moselle", country="FR").get("/api/state").json()
    assert state["air"]["aqi"] == 10 or state["air"]["source"] == "demo"  # demo mode uses invented air data
    assert state["alerts"]["status"] == "ok" and state["alerts"]["items"]
    assert state["ephemeris"]["nameday"]
    assert state["widgets"] == {"chart": True, "second_clock": ""}


@respx.mock
def test_real_mode_reads_the_services(tmp_path):
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=httpx.Response(500))
    respx.get(air.URL).mock(return_value=httpx.Response(200, json={"current": {"european_aqi": 10, "uv_index": 1.0}}))
    respx.get(alerts.FEED.format(slug="france")).mock(
        return_value=httpx.Response(200, text=feed(entry("Moselle", "Yellow Wind Warning issued for France - Moselle")))
    )
    respx.get(ephemeris.NAMEDAY_URL).mock(return_value=httpx.Response(200, json={"data": {"namedays": {"fr": "Denis"}}}))
    state = client(tmp_path, widget_alerts=True, alerts_area="Moselle", country="FR").get("/api/state").json()
    assert state["air"]["aqi"] == 10
    assert [(a["kind"], a["level"]) for a in state["alerts"]["items"]] == [("wind", 1)]
    assert state["ephemeris"]["nameday"] == "Denis"


def test_switched_off_extras_are_absent_and_alerts_say_why(tmp_path):
    off = client(tmp_path, demo=True, widget_air=False, widget_ephemeris=False).get("/api/state").json()
    assert off["air"] is None and off["alerts"] is None and off["ephemeris"] is None
    no_area = client(tmp_path, demo=True, widget_alerts=True).get("/api/state").json()
    assert no_area["alerts"] == {"status": "no_area", "items": []}
    abroad = client(tmp_path, widget_alerts=True, alerts_area="Tokyo", country="JP", widget_air=False, widget_ephemeris=False).get("/api/state").json()
    assert abroad["alerts"]["status"] == "unsupported"


@respx.mock
def test_a_dead_warning_feed_does_not_blank_the_screen(tmp_path):
    respx.get("https://api.open-meteo.com/v1/forecast").mock(return_value=httpx.Response(500))
    respx.get(alerts.FEED.format(slug="france")).mock(side_effect=httpx.ConnectError("down"))
    state = client(tmp_path, widget_alerts=True, alerts_area="Moselle", country="FR", widget_air=False, widget_ephemeris=False).get("/api/state").json()
    assert state["alerts"]["status"] == "error" and state["errors"]["alerts"] == "ConnectError"
