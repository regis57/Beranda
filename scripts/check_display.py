#!/usr/bin/env python3
"""Check the display page's own behaviour in a real browser, with a fake clock.

    python scripts/check_display.py

Each check below was written against a bug the screen really had, and failed before its fix:
an ongoing holiday missing from the agenda, the Korean clock without its colon, TV channels
past the fourth page never shown, a removed radio station still played, a new photo interval
ignored, and the side column's line on the wrong edge in right-to-left languages.

Needs `pip install playwright` and a Chromium (set CHROMIUM_PATH if it is not found). The
state the page reads is the demo's, changed on the way in, so no outside site is needed.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from beranda.app import create_app
from beranda.config import Config


def free_port() -> int:
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_chromium() -> str | None:
    for candidate in (os.environ.get("CHROMIUM_PATH"), "/opt/pw-browsers/chromium"):
        if candidate and Path(candidate).exists():
            return candidate
    for name in ("chromium", "chromium-browser", "google-chrome"):
        found = subprocess.run(["which", name], capture_output=True, text=True, check=False).stdout.strip()
        if found:
            return found
    return None


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    cfg = replace(Config(), cache_dir=tmp / "cache", demo=True, language="fr",
                  news_enabled=False, history_enabled=False)
    app = create_app(cfg, config_path=tmp / "config.toml")
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    time.sleep(1.5)
    base = f"http://127.0.0.1:{port}"

    problems: list[str] = []

    def want(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
        if not ok:
            problems.append(what)

    # Every page below reads the demo state with these changes laid over it; a check changes
    # `extra` between polls to play the owner editing the settings while the screen is open.
    extra: dict = {}

    def patched(route) -> None:
        response = route.fetch()
        state = response.json()
        state["config"]["location"]["timezone"] = "Europe/Paris"
        state.update(extra)
        route.fulfill(response=response, body=json.dumps(state))

    # Sunday 18 October 2026, 10:00 in Paris.
    sunday = datetime(2026, 10, 18, 8, 0, tzinfo=timezone.utc)

    with sync_playwright() as p:
        launch = {"args": ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"]}
        if chromium := find_chromium():
            launch["executable_path"] = chromium
        browser = p.chromium.launch(**launch)

        def settle_poll(page) -> None:
            # Past the next poll; its answer comes back in real time, not on the fake clock.
            page.clock.run_for(61_000)
            page.wait_for_timeout(800)
            page.clock.run_for(100)

        def open_page(query: str = "", width: int = 1280, height: int = 800):
            page = browser.new_page(viewport={"width": width, "height": height})
            page.clock.install(time=sunday)
            page.route("**/api/state*", patched)
            page.route("**/api/photos/**", lambda r: r.fulfill(status=404))
            page.goto(f"{base}/{query}")
            page.wait_for_selector("body[data-ready=true]")
            page.clock.run_for(500)
            return page

        # A holiday that began yesterday is still going on today: it belongs under "today",
        # in the list and in what the screen reads out.
        extra.clear()
        extra["events"] = [
            {"title": "Vacances Bretagne", "start": "2026-10-17", "end": "2026-10-31", "all_day": True, "calendar": 0},
            {"title": "Fini hier", "start": "2026-10-16", "end": "2026-10-18", "all_day": True, "calendar": 0},
            {"title": "Dentiste", "start": "2026-10-20T09:15:00+02:00", "end": "2026-10-20T10:00:00+02:00",
             "all_day": False, "calendar": 0},
        ]
        page = open_page()
        rows = page.eval_on_selector_all("#upcoming li", "e => e.map((x) => x.textContent)")
        want(any("Vacances Bretagne" in r and "Aujourd" in r for r in rows),
             f"an all-day event that started yesterday is listed under today ({rows})")
        want(not any("Fini hier" in r for r in rows), "an event that ended yesterday is not listed")
        said = page.evaluate("import('/static/display.js').then((m) => m.daySummary())")
        want("Vacances Bretagne" in said, f"reading the day out loud includes it ({said!r})")
        # Tomorrow is the next calendar day, also on the night the clocks go back (25 h long).
        nxt = page.evaluate("import('/static/display.js').then((m) => m.nextDayKey && [m.nextDayKey('2026-10-25'),"
                            " m.nextDayKey('2027-03-27'), m.nextDayKey('2026-12-31')])")
        want(nxt == ["2026-10-26", "2027-03-28", "2027-01-01"], f"tomorrow is the next calendar day ({nxt})")
        page.close()

        # The Korean clock puts the day period first ("오후 2:20"): the colon must stay.
        extra.clear()
        page = open_page("?lang=ko")
        hm = page.text_content("#hm")
        want(":" in hm, f"the Korean clock keeps its colon ({hm!r})")
        page.close()

        # A hundred TV channels: every page must come round, even though the screen is redrawn
        # every minute (the clock) and at every poll.
        extra.clear()
        extra["tv"] = {"status": "ok", "from": "20:00", "to": "23:00", "programmes": [
            {"channel": f"C{n:02d}", "start": "21:00", "title": f"Show {n}"} for n in range(1, 101)]}
        page = open_page()
        seen = set()
        for _ in range(400):
            page.clock.run_for(3000)
            seen.update(page.eval_on_selector_all("#tv-list .tv-chan", "e => e.map((x) => x.textContent)"))
        want("C100" in seen and len(seen) == 100, f"every TV channel is shown in turn ({len(seen)} of 100 seen)")
        page.close()

        # A favourite station removed while it plays: the box forgets it, the button never plays it.
        extra.clear()
        stations = [{"name": n, "url": f"{base}/stream-{n}.mp3", "uuid": n} for n in ("Alpha", "Bravo", "Charlie")]
        extra["radio"] = {"stations": stations, "volume": 50}
        page = open_page()
        page.click("#radio-next")
        page.clock.run_for(500)
        before = page.evaluate("document.getElementById('radio-audio').getAttribute('src')")
        extra["radio"] = {"stations": [stations[0], stations[2]], "volume": 50}
        settle_poll(page)
        # The name is replaced by an error line here (the stream is a stand-in), so read the
        # button's label, which always names the station the button would play.
        name = page.get_attribute("#radio-toggle", "aria-label")
        page.click("#radio-toggle")
        page.clock.run_for(500)
        after = page.evaluate("document.getElementById('radio-audio').getAttribute('src') || ''")
        want(before.endswith("Bravo.mp3"), f"the next station plays first ({before})")
        want("Bravo" not in name, f"a removed station leaves the radio box ({name!r})")
        want("Bravo" not in after, f"the play button does not play a removed station ({after!r})")
        page.close()

        # A new photo interval is used at the next poll, without waiting for a new photo.
        extra.clear()
        extra["photos"] = {"names": ["a.jpg", "b.jpg", "c.jpg"], "interval": 20}
        page = open_page()
        shown: list[str] = []
        page.on("request", lambda r: "/api/photos/" in r.url and shown.append(r.url))
        extra["photos"] = {"names": ["a.jpg", "b.jpg", "c.jpg"], "interval": 300}
        settle_poll(page)  # the next poll brings the new interval
        shown.clear()
        page.clock.run_for(240_000)
        want(len(shown) == 0, f"a slower photo interval is used after the next poll ({len(shown)} changes in 4 min)")
        page.close()

        # Right to left: the side column's line sits between it and the board, not on the screen edge.
        extra.clear()
        page = open_page("?lang=ar")
        border = page.eval_on_selector(".side", "e => [getComputedStyle(e).borderRightWidth, getComputedStyle(e).borderLeftWidth]")
        want(border == ["1px", "0px"], f"in Arabic the side column's line faces the board ({border})")
        page.close()

        browser.close()
    server.should_exit = True
    if problems:
        print(f"\n{len(problems)} problem(s) on the display page.")
        return 1
    print("\nThe display page behaves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
