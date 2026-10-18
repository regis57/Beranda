"""Regressions for the server and its data sources: each test here failed before its fix."""

from __future__ import annotations

import asyncio
import io
import logging
import zipfile
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from beranda import app as app_mod
from beranda import doctor, tls
from beranda.cache import Cache
from beranda.config import Config
from beranda.providers import air, alerts, calendar_ics, photos, weather

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


def _client(tmp_path, now, **kw):
    cfg = replace(Config(), cache_dir=tmp_path / "cache", news_enabled=False, history_enabled=False,
                  widget_air=False, widget_ephemeris=False, **kw)
    return TestClient(app_mod.create_app(cfg, now_fn=lambda: now), client=("127.0.0.1", 50000))


# ---- photos -----------------------------------------------------------------------------------
def test_a_photo_folder_beranda_may_not_open_hides_the_tile_instead_of_failing(tmp_path, monkeypatch):
    locked = tmp_path / "locked" / "Pictures"
    real_is_dir = Path.is_dir

    def is_dir(self):
        # Python 3.11-3.13 raise here when a parent folder cannot be entered (ProtectHome=yes).
        if str(self).startswith(str(locked.parent)):
            raise PermissionError(13, "Permission denied")
        return real_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", is_dir)
    assert photos.list_photos(locked) == []
    now = datetime(2026, 10, 18, 9, 0, tzinfo=UTC)
    with respx.mock:
        respx.get(weather.URL).mock(return_value=httpx.Response(500))
        response = _client(tmp_path, now, photos_folder=str(locked)).get("/api/state")
    assert response.status_code == 200


def test_a_picture_that_vanishes_while_listing_is_skipped(tmp_path, monkeypatch):
    (tmp_path / "a.jpg").write_bytes(JPEG)
    (tmp_path / "b.jpg").write_bytes(JPEG)
    real_stat = Path.stat

    def stat(self, *a, **k):
        if self.name == "b.jpg":
            raise FileNotFoundError(2, "gone")
        return real_stat(self, *a, **k)

    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    assert photos.list_photos(tmp_path) == ["a.jpg"]


def _zip(names):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, JPEG + name.encode())
    buffer.seek(0)
    return buffer


def test_dropbox_pictures_with_clashing_names_are_all_kept(tmp_path):
    names = ["Summer 2024/IMG_0001.JPG", "Christmas 2024/IMG_0001.JPG", "家族/海.jpg", "家族/山.jpg", "Семья/Море.jpg"]
    result = photos.extract_zip(_zip(names), tmp_path)
    assert result["total"] == 5
    again = photos.extract_zip(_zip(names), tmp_path)
    assert again == {"added": 0, "removed": 0, "total": 5}  # names are stable between syncs


# ---- weather warnings -------------------------------------------------------------------------
def _feed(area, expires):
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2">'
        f"<entry><title>Red Flood Warning issued for France - {area}</title>"
        f"<cap:areaDesc>{area}</cap:areaDesc><cap:event>Severe flood warning</cap:event>"
        f"<cap:severity>Extreme</cap:severity><cap:status>Actual</cap:status>"
        f"<cap:onset>2026-10-18T08:00:00+00:00</cap:onset><cap:expires>{expires}</cap:expires></entry></feed>"
    )


def test_an_expired_warning_is_dropped_even_from_the_cached_copy(tmp_path, monkeypatch):
    clock = {"t": datetime(2026, 10, 18, 9, 0, tzinfo=UTC)}
    monkeypatch.setattr("beranda.cache.time.time", lambda: clock["t"].timestamp())
    route = respx.mock(assert_all_called=False)
    with route:
        route.get(weather.URL).mock(return_value=httpx.Response(500))
        feed = route.get(alerts.FEED.format(slug="france"))
        feed.mock(return_value=httpx.Response(200, text=_feed("Moselle", "2026-10-18T12:00:00+00:00")))
        cfg = replace(Config(), cache_dir=tmp_path / "cache", news_enabled=False, history_enabled=False,
                      widget_air=False, widget_ephemeris=False, widget_alerts=True, alerts_area="Moselle", country="FR")
        cache = Cache(tmp_path / "cache")
        first = asyncio.run(app_mod.build_state(cfg, cache, clock["t"]))
        assert [w["kind"] for w in first["alerts"]["items"]] == ["flood"]
        feed.mock(side_effect=httpx.ConnectError("down"))
        clock["t"] = datetime(2026, 10, 18, 20, 0, tzinfo=UTC)
        later = asyncio.run(app_mod.build_state(cfg, cache, clock["t"]))
    assert later["alerts"]["items"] == []


@pytest.mark.parametrize(
    ("mine", "theirs"),
    [("Rhône", "Bouches-du-Rhône"), ("Savoie", "Haute-Savoie"), ("Haute-Savoie", "Savoie"),
     ("Ain", "Seine-Saint-Denis"), ("Loire", "Loire-Atlantique"), ("Marne", "Val-de-Marne")],
)
def test_a_neighbouring_area_with_a_similar_name_is_not_mine(mine, theirs):
    warning = {"area": theirs, "kind": "wind", "level": 3}
    assert alerts.for_area([warning], mine) == []


@pytest.mark.parametrize(
    ("mine", "theirs"),
    [("Moselle", "Moselle"), ("drome", "Drôme"), ("Barcelona", "Litoral de Barcelona"), ("Düren", "Kreis Düren"),
     ("Bouches du Rhône", "Bouches-du-Rhône")],
)
def test_the_same_area_written_differently_still_matches(mine, theirs):
    warning = {"area": theirs, "kind": "wind", "level": 3}
    assert alerts.for_area([warning], mine) == [warning]


def test_meteoalarm_temperature_spellings_get_their_kind():
    assert alerts._kind("Moderate high-temperature warning") == "heat"
    assert alerts._kind("Severe low-temperature warning") == "cold"


# ---- calendar ---------------------------------------------------------------------------------
ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:dentist
DTSTART:20261102T090000Z
DTEND:20261102T100000Z
SUMMARY:Dentist
END:VEVENT
END:VCALENDAR
"""


def test_offline_on_the_first_of_the_month_the_agenda_keeps_its_last_copy(tmp_path, monkeypatch):
    clock = {"t": datetime(2026, 10, 31, 23, 50, tzinfo=UTC)}
    monkeypatch.setattr("beranda.cache.time.time", lambda: clock["t"].timestamp())
    online = {"up": True}

    async def download(url):
        if not online["up"]:
            raise httpx.ConnectError("down")
        return ICS

    monkeypatch.setattr(calendar_ics, "download", download)
    cfg = replace(Config(), cache_dir=tmp_path / "cache", news_enabled=False, history_enabled=False,
                  widget_air=False, widget_ephemeris=False, ics_urls=("https://example.org/a.ics",))
    cache = Cache(tmp_path / "cache")
    with respx.mock(assert_all_called=False) as route:
        route.get(weather.URL).mock(return_value=httpx.Response(500))
        first = asyncio.run(app_mod.build_state(cfg, cache, clock["t"]))
        assert [e["title"] for e in first["events"]] == ["Dentist"]
        online["up"] = False
        clock["t"] = datetime(2026, 11, 1, 0, 20, tzinfo=UTC)
        later = asyncio.run(app_mod.build_state(cfg, cache, clock["t"]))
    assert [e["title"] for e in later["events"]] == ["Dentist"]
    assert "calendar:0" in later["stale"]


def test_webcals_links_are_downloaded_over_https():
    assert calendar_ics.normalise_url("webcals://host.example/x.ics") == "https://host.example/x.ics"
    assert calendar_ics.normalise_url("WEBCAL://host.example/x.ics") == "https://host.example/x.ics"


CANCELLED = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:choir
DTSTART:20261006T180000Z
DTEND:20261006T190000Z
RRULE:FREQ=WEEKLY;COUNT=4
SUMMARY:Choir
END:VEVENT
BEGIN:VEVENT
UID:choir
RECURRENCE-ID:20261020T180000Z
DTSTART:20261020T180000Z
DTEND:20261020T190000Z
STATUS:CANCELLED
SUMMARY:Choir
END:VEVENT
BEGIN:VEVENT
UID:party
DTSTART:20261024T180000Z
DTEND:20261024T190000Z
STATUS:CANCELLED
SUMMARY:Party
END:VEVENT
END:VCALENDAR
"""


def test_cancelled_events_are_not_shown():
    got = calendar_ics.events_from_ics(CANCELLED, date(2026, 10, 1), date(2026, 11, 30), "UTC")
    assert [e["start"][:10] for e in got] == ["2026-10-06", "2026-10-13", "2026-10-27"]


def test_a_huge_calendar_file_is_not_read_to_the_end(monkeypatch):
    monkeypatch.setattr(calendar_ics, "MAX_ICS_BYTES", 100_000)
    sent = {"bytes": 0}

    async def body():
        for _ in range(100):
            sent["bytes"] += 10_000
            yield b"x" * 10_000

    with respx.mock:
        respx.get("https://example.org/big.ics").mock(return_value=httpx.Response(200, content=body()))
        with pytest.raises(ValueError, match="too large"):
            asyncio.run(calendar_ics.download("https://example.org/big.ics"))
    assert sent["bytes"] < 200_000


def test_a_small_calendar_still_downloads():
    with respx.mock:
        respx.get("https://example.org/a.ics").mock(return_value=httpx.Response(200, text=ICS))
        assert "Dentist" in asyncio.run(calendar_ics.download("webcals://example.org/a.ics"))


# ---- certificate ------------------------------------------------------------------------------
def test_starting_before_the_network_keeps_the_accepted_certificate(tmp_path, monkeypatch):
    if not tls.openssl_available():
        pytest.skip("openssl is needed to make a certificate")
    address = {"ip": "192.168.1.50"}
    monkeypatch.setattr(tls, "lan_ip", lambda: address["ip"])
    cert, _ = tls.ensure_certificate(tmp_path / "tls")
    accepted = cert.read_bytes()
    address["ip"] = None
    tls.ensure_certificate(tmp_path / "tls")
    assert cert.read_bytes() == accepted
    address["ip"] = "192.168.1.50"
    tls.ensure_certificate(tmp_path / "tls")
    assert cert.read_bytes() == accepted
    address["ip"] = "192.168.1.77"  # a really new address still needs a new certificate
    tls.ensure_certificate(tmp_path / "tls")
    assert cert.read_bytes() != accepted


# ---- command line -----------------------------------------------------------------------------
def test_doctor_reads_the_settings_file_given_with_config(tmp_path, monkeypatch, capsys):
    other = tmp_path / "other.toml"
    other.write_text('[location]\nname = "Berlin"\nlatitude = 52.52\nlongitude = 13.4\n'
                     'timezone = "Europe/Berlin"\n[server]\nport = 9090\n')
    seen = {}

    async def network(cfg):
        seen["port"] = cfg.port
        return []

    monkeypatch.setattr(doctor, "_services", lambda: [])
    monkeypatch.setattr(doctor, "_network", network)
    monkeypatch.setattr(doctor, "_fonts", lambda: [])
    monkeypatch.setattr(doctor, "_unreadable_settings", lambda: None)
    from beranda.__main__ import main

    with pytest.raises(SystemExit):
        main(["doctor", "--config", str(other)])
    assert str(other) in capsys.readouterr().out and seen["port"] == 9090


def test_download_addresses_never_reach_the_journal(tmp_path, monkeypatch):
    import beranda.__main__ as cli

    class Server:
        def run(self):
            pass

    monkeypatch.setattr(cli.tls, "make_server", lambda *a, **k: Server())
    root = logging.getLogger()
    old = root.level, logging.getLogger("httpx").level, logging.getLogger("httpcore").level
    root.setLevel(logging.INFO)
    try:
        cli.main(["--config", str(tmp_path / "config.toml"), "--port", "8099"])
        assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)
        assert not logging.getLogger("httpcore").isEnabledFor(logging.INFO)
    finally:
        root.setLevel(old[0])
        logging.getLogger("httpx").setLevel(old[1])
        logging.getLogger("httpcore").setLevel(old[2])


# ---- air and weather --------------------------------------------------------------------------
def test_a_us_aqi_on_a_band_edge_belongs_to_the_lower_band():
    assert air.parse({"current": {"us_aqi": 50}}, us_scale=True)["aqi_level"] == 0
    assert air.parse({"current": {"us_aqi": 51}}, us_scale=True)["aqi_level"] == 1
    assert air.parse({"current": {"us_aqi": 100}}, us_scale=True)["aqi_level"] == 1
    assert air.parse({"current": {"us_aqi": 101}}, us_scale=True)["aqi_level"] == 2
    assert air.parse({"current": {"us_aqi": 50.6}}, us_scale=True)["aqi_level"] == 1  # shown as 51
    assert air.parse({"current": {"european_aqi": 20}})["aqi_level"] == 1  # the EU scale is unchanged


def test_rain_amounts_stay_in_millimetres_in_imperial_mode():
    assert weather.build_params(1.0, 2.0, "imperial")["precipitation_unit"] == "mm"
    assert weather.build_params(1.0, 2.0, "imperial")["temperature_unit"] == "fahrenheit"

