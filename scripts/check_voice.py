#!/usr/bin/env python3
"""Check the voice button in a real browser, with a stand-in for the speech service.

    python scripts/check_voice.py

The microphone only listens while a tap on the button asked it to (the always-on wake word
of 0.17.2-0.17.7 was taken out again). What stays checked: the button hears and answers, a
browser that answers nothing at all does not leave the button stuck, a computer with no
microphone is told so before and after, and one that has an unusable microphone (Bluetooth
in music mode...) gets the right advice instead of "plug one in".

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

# Behaves like a browser's speech service: one listening at a time, ended by a result.
STAND_IN = """
window.__live = 0; window.__spoken = [];
window.speechSynthesis.speak = (u) => { window.__spoken.push(u.text); if (u.onstart) u.onstart(); };
class FakeRec {
  start() {
    window.__live += 1;
    this.running = true; window.__recs = (window.__recs || []).concat(this);
    setTimeout(() => this.onstart && this.onstart(), 0);
  }
  stop() { if (!this.running) return; this.running = false; window.__live -= 1; setTimeout(() => this.onend && this.onend(), 0); }
}
window.SpeechRecognition = FakeRec;
Object.defineProperty(window, 'isSecureContext', { value: true });
window.__latest = () => (window.__recs || []).filter((r) => r.running).slice(-1)[0];
window.__hear = (t) => { const r = window.__latest(); if (!r) return false;
  r.onresult({ resultIndex: 0, results: [[{ transcript: t }]] }); if (!r.continuous) r.stop(); return true; };
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
    cfg = from_dict({"demo": True, "language": "fr", "voice": {"enabled": True}})
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

        # The ordinary road: tap the button, speak, hear the answer out loud.
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(STAND_IN)
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_timeout(2500)
        want(page.evaluate("window.__live") == 0, "nothing listens until the button is tapped")
        page.click("#mic")
        page.wait_for_timeout(500)
        want(page.evaluate("window.__live") == 1, "the button is listening")
        want(page.evaluate("window.__hear('quelle heure est-il')"), "something is listening for the button")
        page.wait_for_timeout(1200)
        want("Il est" in page.text_content("#toast"), "the button gets an answer")
        want(len(page.evaluate("window.__spoken")) >= 1, "the answer is spoken out loud")
        want(page.evaluate("window.__live") == 0, "the microphone is let go afterwards")
        page.close()

        # The browser sometimes answers nothing at all: no words, no error, no end.
        # The button must not stay stuck on "Listening..." for ever.
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(STAND_IN + "FakeRec.prototype.stop = function () {};")
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_timeout(2500)
        page.click("#mic")
        page.wait_for_timeout(14_000)  # the page gives up on a silent browser after 12 s
        want("…" not in (page.text_content("#toast") or "") or "micro" in page.text_content("#toast").lower(),
             "a browser that answers nothing does not leave the button stuck")
        said = page.text_content("#toast") or ""
        want("no answer" not in said and "(" not in said, f"a silent browser is told in words, not a code ({said!r})")
        page.close()

        # The sentence is heard but Beranda does not answer (restarting, or voice switched off
        # meanwhile): say that, not "microphone unavailable" with an English code after it.
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(STAND_IN)
        page.route("**/api/voice", lambda route: route.fulfill(status=500, body="boom"))
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_timeout(2500)
        page.click("#mic")
        page.wait_for_timeout(500)
        page.evaluate("window.__hear('quelle heure est-il')")
        page.wait_for_timeout(1200)
        said = page.text_content("#toast") or ""
        want("HTTP" not in said and "Micro" not in said and len(said) > 10,
             f"a Beranda that does not answer is told in words ({said!r})")
        page.close()

        # A computer with no microphone at all: say so in words, before and after.
        nomic = browser.new_context(viewport={"width": 1100, "height": 900})
        nomic.add_init_script(STAND_IN + """
            navigator.mediaDevices.enumerateDevices = async () => [{ kind: 'videoinput' }];
            FakeRec.prototype.start = function () { setTimeout(() => this.onerror && this.onerror({ error: 'audio-capture' }), 30); };
        """)
        settings = nomic.new_page()
        settings.goto(f"http://127.0.0.1:{port}/admin")
        settings.wait_for_timeout(2500)
        want("micro" in settings.text_content("#voice-check").lower(),
             "the settings page says there is no microphone before anyone switches voice on")
        want(settings.eval_on_selector_all("#form h2 .num", "e => e.map((x) => Number(x.textContent))")
             == list(range(1, 18)), "the boxes are numbered in order")
        screen = nomic.new_page()
        screen.goto(f"http://127.0.0.1:{port}/")
        screen.wait_for_timeout(2500)
        screen.click("#mic")
        screen.wait_for_timeout(800)
        said = screen.text_content("#toast")
        want("audio-capture" not in said and len(said) > 10, f"the screen says what is wrong, not a code ({said!r})")
        nomic.close()

        # A microphone IS there (a Bluetooth headset) but the browser cannot capture from it:
        # "plug one in" would be the wrong advice, so the settings page must say something else.
        listed = browser.new_context(viewport={"width": 1100, "height": 900})
        listed.add_init_script(STAND_IN + """
            navigator.mediaDevices.enumerateDevices = async () => [{ kind: 'audioinput', label: 'Bluetooth headset' }];
            FakeRec.prototype.start = function () { setTimeout(() => this.onerror && this.onerror({ error: 'audio-capture' }), 30); };
        """)
        bt = listed.new_page()
        bt.goto(f"http://127.0.0.1:{port}/admin")
        bt.wait_for_timeout(2500)
        bt.click("#voice-test")
        bt.wait_for_timeout(1200)
        advice = bt.text_content("#voice-test-msg")
        want(len(advice) > 120 and "Bluetooth" in advice,
             "a microphone that is there but unusable gets the right advice, not \"plug one in\"")
        browser.close()
    server.should_exit = True
    if problems:
        print(f"\n{len(problems)} problem(s): " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
