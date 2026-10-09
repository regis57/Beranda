"""The diagnostic file helps find a bug, and must never carry a secret."""

import logging
from dataclasses import replace

from fastapi.testclient import TestClient

from beranda import diagnostics
from beranda.app import create_app
from beranda.config import Config

SECRETS = ("SECRETCAL", "SECRETDROP", "SECRETFEED", "SECRETGUIDE", "4821", "SECRETPAGE", "SECRETLOG")


def _client(tmp_path):
    cfg = replace(
        Config(),
        cache_dir=tmp_path / "c",
        demo=True,
        ics_urls=("https://calendar.google.com/calendar/ical/SECRETCAL/basic.ics",),
        photos_dropbox_url="https://www.dropbox.com/scl/fo/SECRETDROP/h?rlkey=x",
        news_feeds=("https://example.org/rss?token=SECRETFEED",),
        tv_xmltv_url="https://epg.pw/xmltv/epg_FR.xml.gz?key=SECRETGUIDE",
        admin_pin="4821",
        tv_channels=("51767",),
        tv_channel_names=(("51767", "TF1"),),
    )
    return TestClient(create_app(cfg, config_path=tmp_path / "config.toml"), client=("192.168.1.20", 5000))


def test_the_file_is_a_download_with_the_useful_parts(tmp_path):
    client = _client(tmp_path)
    r = client.post("/api/admin/diagnostics", json={"client": {"user_agent": "Chrome/130", "language": "fr-FR"}},
                    headers={"X-Beranda-Pin": "4821"})
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith('attachment; filename="beranda-diagnostic-')
    text = r.text
    for part in ("version:", "== DEVICE ==", "theme: japan", "language: fr", "guide site epg.pw", "TF1",
                 "== WHAT THE DISPLAY SHOWS NOW ==", "browser: Chrome/130", "settings PIN: set"):
        assert part in text, part


def test_no_secret_ever_reaches_the_file(tmp_path):
    client = _client(tmp_path)
    logging.getLogger("beranda.test").warning("could not read https://calendar.google.com/x/SECRETLOG/basic.ics")
    problems = ["GET /config -> HTTP 500 at https://beranda.local:8080/a.js?x=SECRETPAGE"]
    r = client.post("/api/admin/diagnostics", json={"client": {"problems": problems}},
                    headers={"X-Beranda-Pin": "4821"})
    for secret in SECRETS:
        assert secret not in r.text, secret
    assert "calendar.google.com/…" in r.text or "beranda.local/…" in r.text  # addresses cut to the site


def test_the_place_is_rounded_and_addresses_are_cut():
    assert diagnostics.scrub("GET https://a.example/b/c?token=Z failed") == "GET https://a.example/… failed"
    assert diagnostics.site("https://epg.pw/xmltv/x.gz?key=1") == "epg.pw" and diagnostics.site("") == ""


def test_a_broken_display_still_gives_a_file(tmp_path):
    from datetime import UTC, datetime

    text = diagnostics.build(
        Config(), runtime_info={"port": 8080, "config_exists": False}, state=None, state_problem="ProxyError",
        client={}, photo_folder=tmp_path, own_photos=0, shown_photos=0, now=datetime.now(UTC),
    )
    assert "could not be read: ProxyError" in text and "== RECENT LOG LINES" in text
