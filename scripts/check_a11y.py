#!/usr/bin/env python3
"""Check both pages against the accessibility rules (WCAG 2.1 AA) with axe-core, and walk
the settings page with the Tab key.

    python scripts/check_a11y.py [--axe node_modules/axe-core/axe.min.js]

Needs `pip install playwright`, a Chromium (set CHROMIUM_PATH if it is not found) and
axe-core (`npm i --no-save axe-core`). Exits non-zero on any violation, so CI fails when a
change takes something away from people who use a screen reader or the keyboard.

The pages forbid every script but their own (a strict Content-Security-Policy, which is
right); the checker is injected with that policy switched off, for this check only.
"""

from __future__ import annotations

import argparse
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
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from beranda.app import create_app
from beranda.config import Config

RULES = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
# The screen is checked by day and by night on purpose: left to the clock, a run only ever saw
# one of the two, and a colour too light by day failed daytime runs only (0.18.1).
PAGES = (("display by day", "/?mode=light", 1280, 800), ("display by night", "/?mode=night", 1280, 800),
         ("settings", "/admin", 1280, 2000))


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--axe", default="node_modules/axe-core/axe.min.js")
    parser.add_argument("--language", default="fr")
    args = parser.parse_args()
    axe = Path(args.axe)
    if not axe.is_file():
        print(f"axe-core not found at {axe}: run `npm i --no-save axe-core` first", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp())
    cfg = replace(Config(), cache_dir=tmp / "cache", demo=True, language=args.language,
                  news_enabled=False, history_enabled=False)
    app = create_app(cfg, config_path=tmp / "config.toml")
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    time.sleep(1.5)

    failed = False
    with sync_playwright() as p:
        launch = {"args": ["--no-sandbox"]}
        if chromium := find_chromium():
            launch["executable_path"] = chromium
        browser = p.chromium.launch(**launch)
        for name, path, width, height in PAGES:
            page = browser.new_page(viewport={"width": width, "height": height}, bypass_csp=True)
            page.goto(f"http://127.0.0.1:{port}{path}")
            page.wait_for_timeout(2500)
            page.add_script_tag(content=axe.read_text())
            result = page.evaluate("axe.run(document, {runOnly: {type: 'tag', values: %s}})" % json.dumps(RULES))
            violations = result["violations"]
            print(f"{name}: {len(result['passes'])} rules pass, {len(violations)} violations")
            for v in violations:
                failed = True
                targets = ", ".join(n["target"][0] for n in v["nodes"][:4])
                print(f"  [{v['impact']}] {v['id']}: {v['help']} ({len(v['nodes'])}x) e.g. {targets}")
            if name == "settings":
                # Everything on the settings page must be reachable with the Tab key alone.
                reached = set()
                for _ in range(200):
                    page.keyboard.press("Tab")
                    reached.add(page.evaluate("document.activeElement.id || document.activeElement.tagName"))
                if len(reached) < 50:
                    failed = True
                    print(f"  the Tab key only reaches {len(reached)} things on the settings page")
                else:
                    print(f"  the Tab key reaches {len(reached)} different things")
            page.close()
        browser.close()
    server.should_exit = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
