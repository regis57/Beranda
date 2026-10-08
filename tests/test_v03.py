import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from beranda import config
from beranda.app import create_app
from beranda.config import Config
from beranda.providers import almanac, calendar_ics, equinox, news_catalog, phenology, seasons
from beranda.providers.specialdays import holiday_language
from tests.test_news import RSS

WEB = Path(__file__).parent.parent / "src" / "beranda" / "web"
LOCAL = ("192.168.1.20", 5000)


# ---------------------------------------------------------------- languages ---------
def test_language_codes_are_normalised():
    assert config.normalise_language("pt_br") == "pt-BR"
    assert config.normalise_language("FR") == "fr"
    assert config.normalise_language("") == "en" and config.normalise_language("<script>") == "en"


def test_holiday_names_follow_the_display_language():
    assert holiday_language("SN", "fr") == "fr_SN"
    assert holiday_language("BR", "pt-BR") == "pt_BR"
    assert holiday_language("KE", "sw") == "sw"
    assert holiday_language("FR", "en") == "en_US"
    assert holiday_language("ZA", "af") is None  # no translation: the country's default


def _keys(d, prefix=""):
    out = set()
    for k, v in d.items():
        out |= _keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {prefix + k}
    return out


def test_every_display_language_is_complete():
    english = _keys(json.loads((WEB / "i18n" / "en.json").read_text()))
    for path in (WEB / "i18n").glob("*.json"):
        if path.stem == "pt-BR":
            continue  # only overrides European Portuguese
        missing = english - _keys(json.loads(path.read_text()))
        assert not missing, (path.name, sorted(missing)[:5])


def test_settings_page_translations_are_complete_where_offered():
    english = _keys(json.loads((WEB / "i18n" / "admin" / "en.json").read_text()))
    for code in ("fr", "de", "es", "it", "pt", "id", "ar", "sw"):
        data = json.loads((WEB / "i18n" / "admin" / f"{code}.json").read_text())
        assert english == _keys(data), code
    for code in ("pt-BR",):
        assert _keys(json.loads((WEB / "i18n" / "admin" / f"{code}.json").read_text())) <= english


def test_placeholders_survive_translation():
    import re

    english = json.loads((WEB / "i18n" / "admin" / "en.json").read_text())
    for path in (WEB / "i18n" / "admin").glob("*.json"):
        data = json.loads(path.read_text())
        for key, text in data.items():
            if isinstance(text, str):
                assert set(re.findall(r"{\w+}", text)) == set(re.findall(r"{\w+}", english[key])), (path.name, key)


# ---------------------------------------------------------------- seasons -----------
def test_equinoxes_and_solstices_land_on_the_right_day():
    assert equinox.local_day(2026, "march", "UTC") == date(2026, 3, 20)
    assert equinox.local_day(2026, "june", "UTC") == date(2026, 6, 21)
    assert equinox.local_day(2026, "september", "Europe/Paris") == date(2026, 9, 23)
    assert equinox.local_day(2026, "december", "UTC") == date(2026, 12, 21)


def test_seasons_flip_south_of_the_equator():
    north = equinox.season(date(2026, 10, 9), "Europe/Lisbon", 38.7)
    south = equinox.season(date(2026, 10, 9), "America/Sao_Paulo", -23.5)
    assert north["season"] == "autumn" and south["season"] == "spring"
    assert north["next_change"] == "2026-12-21" and north["days_left"] == 73


def test_almanac_sayings():
    es = almanac.current(date(2026, 4, 2), "Europe/Madrid", 40.4, "es")
    assert es["sub"]["en"] == "En abril, aguas mil." and es["title_key"] == "seasons.spring"
    it = almanac.current(date(2026, 8, 2), "Europe/Rome", 41.9, "it")
    assert it["sub"]["en"].startswith("Agosto")
    br = almanac.current(date(2026, 10, 9), "America/Sao_Paulo", -23.5, "pt-BR")
    assert br["title_key"] == "seasons.spring" and br["sub"]["en"] in almanac.DITADOS
    assert all(len(v) == 12 for v in almanac.PROVERBS.values())


def test_phenology():
    assert phenology.current(date(2026, 10, 9))["title"]["de"] == "Vollherbst"
    assert phenology.current(date(2026, 1, 15))["title"]["de"] == "Winter"
    assert phenology.current(date(2026, 4, 30))["title"]["de"] == "Vollfrühling"


def test_every_theme_has_a_season_block_every_day():
    from datetime import timedelta

    day = date(2028, 1, 1)
    while day.year == 2028:
        for theme in seasons.THEMES:
            block = seasons.current(theme, day, "Europe/Paris", 48.0)
            assert block["glyph"] and (block.get("title_key") or block["title"])
        day += timedelta(days=1)


def test_every_theme_has_a_stylesheet():
    for theme in seasons.THEMES:
        assert (WEB / "themes" / f"{theme}.css").is_file(), theme


# ---------------------------------------------------------------- calendar links ----
def test_nextcloud_share_links_become_feeds():
    assert calendar_ics.normalise_url("https://cloud.example.org/apps/calendar/p/AbC123") == \
        "https://cloud.example.org/remote.php/dav/public-calendars/AbC123?export"
    assert calendar_ics.normalise_url("https://c.example/index.php/apps/calendar/p/Z9") == \
        "https://c.example/remote.php/dav/public-calendars/Z9?export"
    assert calendar_ics.normalise_url("https://c.example/remote.php/dav/public-calendars/Z9") == \
        "https://c.example/remote.php/dav/public-calendars/Z9?export"
    assert calendar_ics.normalise_url(" webcal://p01.icloud.com/x ") == "https://p01.icloud.com/x"


# ---------------------------------------------------------------- news: config & state
def test_news_settings_round_trip():
    cfg = config.from_dict({"news": {"enabled": False, "sources": ["city", "g1"], "feeds": ["https://a.example/rss"]}})
    assert cfg.news_enabled is False and cfg.news_sources == ("city", "g1")
    back = config.to_dict(cfg)["news"]
    assert back == {"enabled": False, "sources": ["city", "g1"], "feeds": ["https://a.example/rss"]}
    assert config.from_dict({}).news_sources is None  # automatic by default
    assert "sources" not in config.to_dict(config.from_dict({}))["news"]


def test_news_feeds_must_be_web_links():
    import pytest

    with pytest.raises(ValueError):
        config.from_dict({"news": {"feeds": ["file:///etc/passwd"]}})


@respx.mock
def test_state_merges_headlines_and_survives_a_dead_feed(tmp_path):
    respx.get(news_catalog.BY_ID["g1"]["url"]).mock(return_value=httpx.Response(200, content=RSS))
    respx.get(news_catalog.BY_ID["folha"]["url"]).mock(side_effect=httpx.ConnectError("down"))
    respx.get(url__startswith="https://api.open-meteo.com").mock(return_value=httpx.Response(500))
    cfg = replace(Config(), cache_dir=tmp_path, news_sources=("g1", "folha"), country="BR")
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now = datetime(2026, 10, 9, 0, 30, tzinfo=ZoneInfo("Europe/Paris"))
    state = TestClient(create_app(cfg, now_fn=lambda: now)).get("/api/state").json()
    assert [i["title"] for i in state["news"]["items"]] == ["First & bold headline", "Older one"]
    assert state["news"]["items"][0]["source"] == "g1"  # the catalog name wins
    assert state["errors"]["news:folha"] == "ConnectError"


def test_demo_news_is_localised(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path, demo=True, language="pt-BR")
    state = TestClient(create_app(cfg)).get("/api/state").json()
    assert state["news"]["items"][0]["title"].startswith("Biblioteca")


def test_news_can_be_switched_off(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path, demo=True, news_enabled=False)
    assert TestClient(create_app(cfg)).get("/api/state").json()["news"] is None


# ---------------------------------------------------------------- news: settings page
def _admin(tmp_path):
    cfg = replace(Config(), cache_dir=tmp_path / "c", news_enabled=False)
    return TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=LOCAL), tmp_path / "config.toml"


def test_settings_page_offers_the_catalog_and_the_automatic_choice(tmp_path):
    client, _ = _admin(tmp_path)
    data = client.get("/api/admin/config").json()
    assert data["first_run"] is True
    assert {"id", "name", "lang", "scope"} <= set(data["options"]["news"][0])
    assert "url" not in data["options"]["news"][0]
    assert "pt-BR" in data["options"]["languages"] and "ar" in data["options"]["languages"]
    auto = client.get("/api/admin/news-auto", params={"country": "de", "language": "de", "city": "Köln"}).json()
    assert auto["sources"] == ["city", "tagesschau", "spiegel", "dw-de"]


def test_saving_news_choices(tmp_path):
    client, path = _admin(tmp_path)
    body = {"country": "BR", "language": "pt-BR", "location": {"name": "Recife", "latitude": -8.05,
            "longitude": -34.9, "timezone": "America/Recife"},
            "news": {"enabled": True, "sources": ["city", "g1"], "feeds": ["https://blog.example/feed"]}}
    assert client.put("/api/admin/config", json=body).status_code == 200
    saved = config.load(path)
    assert saved.news_sources == ("city", "g1") and saved.language == "pt-BR"
    assert client.get("/api/admin/config").json()["first_run"] is False
    bad = dict(body, news={"sources": ["not-a-source"]})
    assert client.put("/api/admin/config", json=bad).status_code == 422


@respx.mock
def test_feed_test_button(tmp_path):
    client, _ = _admin(tmp_path)
    respx.get("https://blog.example/feed").mock(return_value=httpx.Response(200, content=RSS))
    ok = client.post("/api/admin/test-feed", json={"url": "https://blog.example/feed"}).json()
    assert ok == {"ok": True, "count": 2, "first": "First & bold headline"}
    respx.get("https://blog.example/html").mock(return_value=httpx.Response(200, text="<html><body>no feed"))
    assert client.post("/api/admin/test-feed", json={"url": "https://blog.example/html"}).json()["ok"] is False
    assert client.post("/api/admin/test-feed", json={"url": "javascript:alert(1)"}).json() == {"ok": False, "error": "NotALink"}
