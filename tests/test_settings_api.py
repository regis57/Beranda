"""Regressions for the settings API: each test here failed before its fix."""

import asyncio
import time
import tomllib
from dataclasses import replace
from itertools import pairwise

import pytest

from beranda import admin, config, limits, urls
from beranda.providers import photos, tv
from tests.test_admin import LOCAL, make, valid_body


def test_a_save_keeps_a_profile_forced_in_the_file_and_every_link(tmp_path, monkeypatch):
    # The board looks like a small Pi, so the automatic limit is lower than the forced one.
    monkeypatch.setattr(limits, "device", lambda: ("Raspberry Pi 3 Model B Plus", 1.0))
    monkeypatch.delenv("BERANDA_PROFILE", raising=False)
    links = [f"https://example.org/{i}.ics" for i in range(15)]
    client, path = make(tmp_path, limits_profile="plus", ics_urls=tuple(links))
    body = valid_body(calendar={"ics_urls": links})  # the page never sends `limits`
    assert client.put("/api/admin/config", json=body).status_code == 200
    saved = tomllib.loads(path.read_text())
    assert saved["limits"]["profile"] == "plus"
    assert saved["calendar"]["ics_urls"] == links


@pytest.mark.parametrize("pin", ["١٢٣٤٥٦", "12 34", " 1234", "12​34"])
def test_a_pin_that_cannot_travel_in_a_header_is_refused(tmp_path, pin):
    client, path = make(tmp_path)
    reply = client.put("/api/admin/config", json=valid_body(pin=pin))
    assert reply.status_code == 422
    assert not path.exists()


def test_an_ordinary_pin_is_still_saved(tmp_path):
    client, path = make(tmp_path)
    assert client.put("/api/admin/config", json=valid_body(pin="1234")).status_code == 200
    assert tomllib.loads(path.read_text())["admin"]["pin"] == "1234"


def test_an_unknown_main_time_zone_is_refused(tmp_path):
    client, path = make(tmp_path)
    body = valid_body()
    body["location"] = {**body["location"], "timezone": "Europe/paris"}
    reply = client.put("/api/admin/config", json=body)
    assert reply.status_code == 422 and "time zone" in reply.json()["detail"]
    assert not path.exists()


def test_another_sites_name_as_host_is_refused(tmp_path):
    client, _ = make(tmp_path)
    evil = {"host": "evil.example:8080"}
    assert client.get("/api/admin/config", headers=evil).status_code == 403
    reply = client.put(
        "/api/admin/config", json=valid_body(pin="999999"),
        headers={**evil, "origin": "http://evil.example:8080"},
    )
    assert reply.status_code == 403
    assert client.get("/api/state", headers=evil).status_code == 403


@pytest.mark.parametrize("host", [
    "beranda.local:8080", "192.168.1.5:8080", "localhost", "[fe80::1]:8080", "beranda",
    "pi.lan", "mirror.home.arpa", "testserver",
])
def test_home_names_still_work(tmp_path, host):
    client, _ = make(tmp_path)
    assert client.get("/api/admin/config", headers={"host": host}).status_code == 200


@pytest.mark.parametrize("bad", ["a​b", "a b", "a‮b", "a b"])
def test_invisible_characters_are_refused_in_an_address(bad):
    with pytest.raises(ValueError, match="does not belong"):
        urls.checked_url(f"https://example.org/{bad}")


def test_accented_letters_still_pass():
    assert urls.checked_url("https://exemple.fr/été")


def test_a_wrong_scheme_message_does_not_repeat_the_address():
    with pytest.raises(ValueError) as caught:
        urls.checked_url("calendar.example.org/private-secret-token")
    assert "secret" not in str(caught.value) and "calendar.example" not in str(caught.value)


def test_a_radio_message_does_not_repeat_the_address():
    with pytest.raises(ValueError) as caught:
        config._parse_station({"url": "stream.example.org/secret-token"})
    assert "secret" not in str(caught.value)


def test_a_hand_set_cache_folder_survives_a_save(tmp_path):
    chosen = tmp_path / "usb-cache"
    path = tmp_path / "config.toml"
    admin.write_config(path, replace(config.Config(), cache_dir=chosen))
    assert config.load(path).cache_dir == chosen


@pytest.mark.parametrize("raw", ["04-31", "02-30", "2023-02-29"])
def test_impossible_key_dates_are_refused(tmp_path, raw):
    client, path = make(tmp_path)
    body = valid_body(key_dates=[{"date": raw, "label": "Mum", "kind": "birth"}])
    assert client.put("/api/admin/config", json=body).status_code == 422
    assert not path.exists()


@pytest.mark.parametrize("raw", ["02-29", "2020-02-29"])
def test_leap_days_are_still_allowed(tmp_path, raw):
    client, _ = make(tmp_path)
    body = valid_body(key_dates=[{"date": raw, "label": "Leap", "kind": "birth"}])
    assert client.put("/api/admin/config", json=body).status_code == 200


def test_finding_tv_channels_does_not_freeze_the_screen(tmp_path, monkeypatch):
    import httpx

    from beranda.app import create_app

    parse_seconds = 0.4
    beats = []

    async def fake_download(url):
        return b"<tv/>"

    def slow_channels(raw):
        time.sleep(parse_seconds)  # stands for a big guide being unpacked and read
        return []

    monkeypatch.setattr(tv, "download", fake_download)
    monkeypatch.setattr(tv, "channels", slow_channels)
    cfg = replace(config.Config(), cache_dir=tmp_path / "cache", news_enabled=False, history_enabled=False)
    app = create_app(cfg, config_path=tmp_path / "config.toml")

    async def heartbeat():
        while True:
            beats.append(time.monotonic())
            await asyncio.sleep(0.02)

    async def run():
        transport = httpx.ASGITransport(app=app, client=LOCAL)
        async with httpx.AsyncClient(transport=transport, base_url="http://beranda.local") as client:
            clock = asyncio.create_task(heartbeat())
            reply = await client.post("/api/admin/test-tv", json={"url": "https://example.org/g.xml"})
            clock.cancel()
        assert reply.json()["ok"] is True

    asyncio.run(run())
    longest = max(b - a for a, b in pairwise(beats))
    assert longest < parse_seconds / 2, f"the server stopped answering for {longest:.2f}s"


def test_two_dropbox_copies_never_run_at_once(tmp_path, monkeypatch):
    running = 0
    most = 0
    calls = 0

    async def fake_sync(link, folder, limit):
        nonlocal running, most, calls
        calls += 1
        running += 1
        most = max(most, running)
        await asyncio.sleep(0.05)
        running -= 1
        return {"added": 1, "removed": 0, "total": 1}

    monkeypatch.setattr(photos, "sync_dropbox", fake_sync)
    cfg = replace(config.Config(), photos_dropbox_url="https://www.dropbox.com/scl/fo/a/h?rlkey=x",
                  photos_folder=str(tmp_path))
    runtime = admin.Runtime(cfg=cfg, config_path=None)

    async def run():
        return await asyncio.gather(runtime.sync_dropbox(), runtime.sync_dropbox())

    results = asyncio.run(run())
    assert all(r["ok"] for r in results)
    assert most == 1 and calls == 1
