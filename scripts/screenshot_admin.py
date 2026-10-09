#!/usr/bin/env python3
"""Screenshots of the settings page.

The town search, the calendar test and the feed test need internet, which a build machine may
not have, so those answers are simulated in the browser. The page, the saving and the
validation are the real ones.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from playwright.sync_api import sync_playwright
from screenshot import find_chromium, free_port, wait_for

from beranda import config
from beranda.admin import write_config

SEARCH = {"results": [
    {"name": "Metz", "region": "Grand Est", "country": "FR",
     "latitude": 49.1193, "longitude": 6.1757, "timezone": "Europe/Paris"},
    {"name": "Metz", "region": "Missouri", "country": "US",
     "latitude": 37.65, "longitude": -94.07, "timezone": "America/Chicago"},
]}
ICS_OK = {"ok": True, "count": 14, "next": ["Yoga", "Dentiste", "Dîner chez Sam"]}
SYSTEM = {"version": "0.4.0", "installed": True, "commit": "a1b2c3d", "branch": "main", "screen": True, "actions": True}
LATEST = {"latest": "0.4.1", "update_available": True}
FEED_OK = {"ok": True, "count": 31, "first": "La médiathèque élargit ses horaires d'ouverture"}


def reply(answer: dict):
    """A route handler that answers with this JSON (Playwright passes route and request)."""

    def handler(route, _request) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(answer))

    return handler


@contextlib.contextmanager
def server(cfg_path: Path):
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "beranda", "--demo", "--config", str(cfg_path),
         "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_for(f"http://127.0.0.1:{port}/api/health")
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--prefix", default="admin")
    parser.add_argument("--lang", default="fr")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="beranda-shot-"))

    filled = tmp / "filled.toml"
    write_config(filled, replace(
        config.Config(),
        language=args.lang,
        ics_urls=("https://calendar.google.com/calendar/ical/demo%40example.org/private-0000/basic.ics",),
        key_dates=(
            config.KeyDate(6, 2, "Léa", "birth", 2018),
            config.KeyDate(3, 14, "Papi", "death", 2014),
            config.KeyDate(9, 21, "Mariage", "anniversary", 2012),
        ),
    ))
    fresh = tmp / "not-yet-created.toml"
    errors: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=find_chromium(), args=["--no-sandbox"])

        def open_page(base: str, width: int, height: int):
            page = browser.new_page(viewport={"width": width, "height": height}, locale=args.lang)
            page.on("console", lambda m: errors.append(m.text) if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for pattern, answer in (("geocode", SEARCH), ("test-ics", ICS_OK), ("test-feed", FEED_OK),
                                    ("system/latest", LATEST), ("system", SYSTEM)):
                page.route(f"**/api/admin/{pattern}", reply(answer))
                page.route(f"**/api/admin/{pattern}?*", reply(answer))
            page.goto(f"{base}/admin")
            page.wait_for_selector("#app:not([hidden])", timeout=15000)
            page.wait_for_timeout(1800)  # the preview iframe and the news preview
            return page

        def shot(page, name: str, selector: str | None = None) -> None:
            target = args.out / f"{args.prefix}{name}.png"
            if selector:  # the fixed save bar would cover the bottom of a section
                page.evaluate("document.querySelector('.savebar').style.visibility = 'hidden'")
                page.locator(selector).screenshot(path=str(target))
                page.evaluate("document.querySelector('.savebar').style.visibility = ''")
            else:
                page.screenshot(path=str(target))
            print("wrote", target)

        with server(filled) as base:
            page = open_page(base, 1280, 900)
            page.click("#ics-list .item button >> nth=0")  # Test the calendar link
            page.wait_for_timeout(300)
            height = page.evaluate("document.documentElement.scrollHeight")
            page.set_viewport_size({"width": 1280, "height": height})
            page.wait_for_timeout(400)
            shot(page, "")
            shot(page, "-calendar", "#sec-cal")
            page.click("#sys-check")
            page.wait_for_timeout(300)
            shot(page, "-screen", "#sec-screen")
            shot(page, "-system", "#sec-system")
            page.uncheck("#news-auto")  # show the lists you can pick from
            page.wait_for_timeout(500)
            page.click("#news-city .src button")  # Test the town news
            page.wait_for_timeout(300)
            shot(page, "-news", "#sec-news")
            page.close()

            page = open_page(base, 1280, 760)
            page.fill("#q", "Metz")
            page.click("#q-go")
            page.wait_for_selector("#q-results:not([hidden])")
            shot(page, "-search")
            page.close()

        with server(fresh) as base:  # first visit: the welcome box
            page = open_page(base, 390, 844)
            shot(page, "-mobile")
            page.close()
        browser.close()

    if errors:
        print("console problems:", *errors, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
