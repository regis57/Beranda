#!/usr/bin/env python3
"""Screenshots of the admin page. The city search and the calendar test need internet, which a
build machine may not have, so those two answers are simulated in the browser (the page and
the save/validate logic are the real ones)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from playwright.sync_api import sync_playwright
from screenshot import find_chromium, free_port, wait_for

from beranda import config

SEARCH = {"results": [
    {"name": "Yogyakarta", "region": "Special Region of Yogyakarta", "country": "ID",
     "latitude": -7.7829, "longitude": 110.3608, "timezone": "Asia/Jakarta"},
    {"name": "Yogyakarta", "region": "Central Java", "country": "ID",
     "latitude": -7.8, "longitude": 110.37, "timezone": "Asia/Jakarta"},
]}
ICS_OK = {"ok": True, "count": 14, "next": ["Yoga", "Dentiste", "Dîner chez Sam"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--prefix", default="admin")
    parser.add_argument("--lang", default="fr")
    parser.add_argument("--theme", default="japan")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    cfg = replace(
        config.Config(),
        language=args.lang,
        theme=args.theme,
        ics_urls=("https://calendar.google.com/calendar/ical/demo%40example.org/private-0000/basic.ics",),
        key_dates=(
            config.KeyDate(6, 2, "Léa", "birth", 2018),
            config.KeyDate(3, 14, "Papi", "death", 2014),
            config.KeyDate(9, 21, "Mariage", "anniversary", 2012),
        ),
    )
    tmp = Path(tempfile.mkdtemp(prefix="beranda-shot-"))
    cfg_path = tmp / "config.toml"
    from beranda.admin import write_config

    write_config(cfg_path, cfg)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "beranda", "--demo", "--config", str(cfg_path),
         "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    errors: list[str] = []
    try:
        wait_for(f"{base}/api/health")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=find_chromium(), args=["--no-sandbox"])

            def open_page(width: int, height: int):
                page = browser.new_page(viewport={"width": width, "height": height})
                page.on("console", lambda m: errors.append(m.text) if m.type in ("error", "warning") else None)
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.route("**/api/admin/geocode*", lambda r: r.fulfill(
                    status=200, content_type="application/json", body=json.dumps(SEARCH)))
                page.route("**/api/admin/test-ics", lambda r: r.fulfill(
                    status=200, content_type="application/json", body=json.dumps(ICS_OK)))
                page.goto(f"{base}/admin")
                page.wait_for_selector("#app:not([hidden])", timeout=15000)
                page.wait_for_timeout(1800)  # let the preview iframe finish loading
                return page

            page = open_page(1280, 1800)
            page.click("#ics-list .item button:has-text('Tester'), #ics-list .item button:has-text('Test')")
            page.wait_for_timeout(300)
            page.screenshot(path=str(args.out / f"{args.prefix}.png"))
            print("wrote", args.out / f"{args.prefix}.png")
            page.close()

            page = open_page(1280, 760)
            page.fill("#q", "Yogya")
            page.click("#q-go")
            page.wait_for_selector("#q-results:not([hidden])")
            page.screenshot(path=str(args.out / f"{args.prefix}-search.png"))
            print("wrote", args.out / f"{args.prefix}-search.png")
            page.close()

            page = open_page(390, 844)
            page.screenshot(path=str(args.out / f"{args.prefix}-mobile.png"), full_page=False)
            print("wrote", args.out / f"{args.prefix}-mobile.png")
            page.close()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)
    if errors:
        print("console problems:", *errors, sep="\n  ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
