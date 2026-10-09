#!/usr/bin/env python3
"""Take reference screenshots of the display, in demo mode, light and night.

    python scripts/screenshot.py [--out docs/screenshots] [--size 1280x800]

Needs `pip install playwright` and a Chromium (set CHROMIUM_PATH if it is not found).
Exits non-zero if the page logs a console error, so it doubles as a smoke test.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

from playwright.sync_api import sync_playwright


def free_port() -> int:
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_chromium() -> str | None:
    if os.environ.get("CHROMIUM_PATH"):
        return os.environ["CHROMIUM_PATH"]
    base = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""))
    for candidate in sorted(base.glob("chromium-*/chrome-linux*/chrome")):
        return str(candidate)
    return None  # let Playwright use its own


def wait_for(url: str, timeout: float = 20) -> None:
    import urllib.request

    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"server did not come up at {url}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("docs/screenshots"))
    parser.add_argument("--size", default="1280x800")
    parser.add_argument("--portrait", action="store_true", help="also capture 800x1280")
    parser.add_argument("--lang", default=None, help="force the UI language (fr, en, ja...)")
    parser.add_argument("--theme", default=None, help="force a theme (japan, indonesia, france)")
    parser.add_argument("--config", default=None, help="config file to start the server with")
    parser.add_argument("--setup", action="store_true", help="show the first-start setup card")
    parser.add_argument("--prefix", default="display")
    args = parser.parse_args()

    width, height = (int(x) for x in args.size.split("x"))
    args.out.mkdir(parents=True, exist_ok=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "beranda", "--demo", "--host", "127.0.0.1", "--port", str(port)]
        + (["--config", args.config] if args.config else []),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    errors: list[str] = []
    try:
        wait_for(f"{base}/api/health")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=find_chromium(), args=["--no-sandbox"])
            shots = [(width, height, "")]
            if args.portrait:
                shots.append((height, width, "-portrait"))
            for w, h, suffix in shots:
                for mode in ("light", "night"):
                    page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
                    page.on(
                        "console",
                        lambda m: errors.append(m.text) if m.type in ("error", "warning") else None,
                    )
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    query = f"?mode={mode}" + (f"&lang={args.lang}" if args.lang else "") + (
                        f"&theme={args.theme}" if args.theme else ""
                    ) + ("&setup=preview" if args.setup else "")
                    page.goto(f"{base}/{query}")
                    page.wait_for_selector("body[data-ready=true]", timeout=15000)
                    page.wait_for_timeout(1700)  # let the colour transition finish
                    target = args.out / f"{args.prefix}-{mode}{suffix}.png"
                    page.screenshot(path=str(target))
                    print("wrote", target)
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
