#!/usr/bin/env python3
"""Check the voice control in a real browser, with a stand-in for the speech service.

    python scripts/check_voice.py

A browser allows ONE listening at a time. The wake word listens all the time, so pressing the
microphone button has to borrow the microphone and give it back; when that went wrong (v0.17.2)
both stopped working and nothing said a word. This checks it, and that a failing speech service
makes Beranda wait longer and longer instead of asking again every second.

Needs `pip install playwright` and a Chromium (set CHROMIUM_PATH if it is not found).
Exits non-zero on any problem.
"""

from __future__ import annotations

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
from beranda.config import from_dict

# Behaves like a browser's speech service, and refuses a second listening, exactly as one does.
STAND_IN = """
window.__live = 0; window.__peak = 0; window.__log = []; window.__spoken = [];
window.speechSynthesis.speak = (u) => { window.__spoken.push(u.text); if (u.onstart) u.onstart(); };
class FakeRec {
  start() {
    if (window.__live > 0) { window.__log.push('REFUSED'); throw new DOMException('already started', 'InvalidStateError'); }
    window.__live += 1; window.__peak = Math.max(window.__peak, window.__live);
    this.running = true; window.__recs = (window.__recs || []).concat(this);
    window.__log.push('start'); setTimeout(() => this.onstart && this.onstart(), 0);
  }
  stop() { if (!this.running) return; this.running = false; window.__live -= 1; setTimeout(() => this.onend && this.onend(), 0); }
}
window.SpeechRecognition = FakeRec;
Object.defineProperty(window, 'isSecureContext', { value: true });
window.__latest = () => (window.__recs || []).filter((r) => r.running).slice(-1)[0];
window.__hear = (t) => { const r = window.__latest(); if (!r) return false;
  r.onresult({ resultIndex: 0, results: [[{ transcript: t }]] }); if (!r.continuous) r.stop(); return true; };
window.__fail = (e) => { const r = window.__latest(); if (r) { r.onerror({ error: e }); r.stop(); } };
"""


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
    cfg = from_dict({"demo": True, "language": "fr", "voice": {"enabled": True, "wake_word": "Beranda"}})
    app = create_app(replace(cfg, cache_dir=tmp / "cache", news_enabled=False, history_enabled=False),
                     config_path=tmp / "config.toml")
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    time.sleep(1.5)

    problems: list[str] = []

    def want(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
        if not ok:
            problems.append(what)

    with sync_playwright() as p:
        launch = {"args": ["--no-sandbox"]}
        if chromium := find_chromium():
            launch["executable_path"] = chromium
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(STAND_IN)
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_timeout(2500)

        want(page.evaluate("window.__live") == 1, "the wake word listens once the screen is up")
        page.click("#mic")
        page.wait_for_timeout(500)
        want(page.evaluate("window.__peak") == 1, "the microphone button does not open a second listening")
        want(page.evaluate("window.__hear('quelle heure est-il')"), "something is listening for the button")
        page.wait_for_timeout(1200)
        want("Il est" in page.text_content("#toast"), "the button gets an answer while the wake word is on")
        page.wait_for_timeout(1500)
        want(page.evaluate("window.__live") == 1, "the wake word gets the microphone back")
        page.evaluate("window.__hear('beranda quel jour on est')")
        page.wait_for_timeout(900)
        want(len(page.evaluate("window.__spoken")) > 1, "the wake word answers, out loud")

        before = page.evaluate("window.__log.filter((x) => x === 'start').length")
        for _ in range(4):
            page.evaluate("window.__fail('network')")
            page.wait_for_timeout(300)
        page.wait_for_timeout(3000)
        tries = page.evaluate("window.__log.filter((x) => x === 'start').length") - before
        want(tries <= 8, f"a failing speech service is left alone (asked again {tries} times, not dozens)")
        want(page.evaluate("window.__log.filter((x) => x === 'REFUSED').length") == 0, "the browser never refuses a listening")
        browser.close()
    server.should_exit = True
    if problems:
        print(f"\n{len(problems)} problem(s): " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
