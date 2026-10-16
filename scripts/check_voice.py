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


# The tests with several pages need what Chrome really does: ONE microphone for the whole
# browser. The pages ask the test itself (exposed functions) whether they may have it; a
# second recognition, in any page, is cut off ("aborted") exactly as Chrome cuts it off.
SHARED = """
window.__mine = null;
class SharedRec {
  start() {
    this.rid = Math.random().toString(36).slice(2);
    window.__micTake(this.rid).then((ok) => {
      if (!ok) { this.onerror && this.onerror({ error: 'aborted' }); this.onend && this.onend(); return; }
      this.running = true; window.__mine = this; this.onstart && this.onstart();
    });
  }
  stop() {
    if (!this.running) return;
    this.running = false; window.__micGive(this.rid);
    if (window.__mine === this) window.__mine = null;
    setTimeout(() => this.onend && this.onend(), 0);
  }
}
window.SpeechRecognition = SharedRec;
Object.defineProperty(window, 'isSecureContext', { value: true });
navigator.mediaDevices.enumerateDevices = async () => [{ kind: 'audioinput', label: 'USB speakerphone' }];
window.speechSynthesis.speak = (u) => { if (u.onstart) u.onstart(); };
window.__hear = (t) => { const r = window.__mine; if (!r) return false;
  r.onresult({ resultIndex: 0, results: [[{ transcript: t }]] }); if (!r.continuous) r.stop(); return true; };
"""


def shared_microphone(context):
    """Expose one browser-wide microphone to every page of `context`; returns its counters."""
    mic = {"holder": None, "page": None, "cut": 0}

    def take(source, rid: str) -> bool:
        if mic["holder"] in (None, rid):
            mic["holder"], mic["page"] = rid, source["page"]
            return True
        mic["cut"] += 1
        return False

    def give(source, rid: str) -> None:
        if mic["holder"] == rid:
            mic["holder"] = mic["page"] = None

    def closed(page) -> None:  # closing a tab frees its microphone, as in a real browser
        if mic["page"] is page:
            mic["holder"] = mic["page"] = None

    context.expose_binding("__micTake", take)
    context.expose_binding("__micGive", give)
    context.on("page", lambda page: page.on("close", closed))
    context.add_init_script(SHARED)
    return mic


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

        # "Somebody took the microphone" after it worked: that passes, so try again later.
        # Right at the start it means there is none: give up rather than ask for ever.
        page.wait_for_timeout(5200)
        page.evaluate("window.__fail('audio-capture')")
        page.wait_for_timeout(3000)
        want(page.evaluate("window.__live") == 1, "a microphone taken away for a moment is waited for, not given up")

        before = page.evaluate("window.__log.filter((x) => x === 'start').length")
        for _ in range(4):
            page.evaluate("window.__fail('network')")
            page.wait_for_timeout(300)
        page.wait_for_timeout(3000)
        tries = page.evaluate("window.__log.filter((x) => x === 'start').length") - before
        want(tries <= 8, f"a failing speech service is left alone (asked again {tries} times, not dozens)")
        want(page.evaluate("window.__log.filter((x) => x === 'REFUSED').length") == 0, "the browser never refuses a listening")
        page.close()

        # The browser sometimes answers nothing at all to the button: no words, no error, no end.
        # The microphone must still come back to the wake word afterwards.
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.add_init_script(STAND_IN)
        page.goto(f"http://127.0.0.1:{port}/")
        page.wait_for_timeout(2500)
        page.click("#mic")
        page.wait_for_timeout(1000)
        want(page.evaluate("window.__live") == 1, "the button is listening")
        page.wait_for_timeout(14_000)  # the page gives up on a silent browser after 12 s
        want(page.evaluate("window.__live") == 1, "a browser that answers nothing does not keep the microphone for ever")
        want(page.evaluate("window.__hear('beranda quelle heure est-il')"), "the wake word is listening again")

        page.close()

        # Two Beranda screens in the SAME browser, sharing ONE microphone as in Chrome. The first
        # keeps it; the second waits. And they must stay that way, not take it from each other
        # every few seconds (v0.17.4-0.17.6 did, and nothing was ever heard).
        together = browser.new_context(viewport={"width": 1280, "height": 800})
        mic = shared_microphone(together)
        first, second = together.new_page(), together.new_page()
        first.goto(f"http://127.0.0.1:{port}/")
        first.wait_for_timeout(2500)
        second.goto(f"http://127.0.0.1:{port}/")
        second.wait_for_timeout(3000)
        holders = [first.evaluate("window.__mine !== null"), second.evaluate("window.__mine !== null")]
        want(holders == [True, False], f"the first screen keeps the microphone, the second waits ({holders})")
        cut_before = mic["cut"]
        first.wait_for_timeout(7000)
        want(mic["cut"] - cut_before <= 1, f"the two screens do not take it from each other (cut off {mic['cut'] - cut_before} times in 7 s)")
        want(first.evaluate("window.__mine !== null"), "the first screen still holds it 7 s later")

        # The settings page shows a little copy of the screen as a preview. That copy must never
        # listen: it was a hidden second screen holding the microphone (found in v0.17.6).
        settings = together.new_page()
        settings.goto(f"http://127.0.0.1:{port}/admin")
        settings.wait_for_timeout(3000)
        preview_listens = settings.frame_locator("#preview").locator("body").evaluate("() => window.__mine !== null")
        want(not preview_listens, "the preview on the settings page never takes the microphone")
        want(first.evaluate("window.__mine !== null"), "the real screen keeps the microphone while the settings page is open")

        # The settings page, in another tab, tests the microphone while a screen's wake word
        # holds it: the screen must step aside, the test must hear, and the screen take it back.
        settings.click("#voice-test")
        settings.wait_for_timeout(1800)
        want(settings.evaluate("window.__mine !== null"), "the settings test gets the microphone from the screen in another tab")
        settings.evaluate("window.__hear('bonjour beranda')")
        settings.wait_for_timeout(600)
        msg = settings.text_content("#voice-test-msg")
        want("bonjour" in msg.lower(), f"the settings test hears what is said ({msg!r})")
        first.wait_for_timeout(2500)
        want(first.evaluate("window.__mine !== null"), "the screen takes the microphone back after the test")

        # The screen that held it is closed: the other one takes over by itself.
        first.goto("about:blank")  # leaving the page, as closing the tab does
        first.close()
        second.wait_for_timeout(3000)
        want(second.evaluate("window.__mine !== null"), "when the first screen is closed, the second one takes over at once")
        together.close()

        # A computer with no microphone at all: say so in words, before and after.
        nomic = browser.new_context(viewport={"width": 1100, "height": 900})
        nomic.add_init_script(STAND_IN + """
            navigator.mediaDevices.enumerateDevices = async () => [{ kind: 'videoinput' }];
            FakeRec.prototype.start = function () { setTimeout(() => this.onerror && this.onerror({ error: 'audio-capture' }), 30); };
        """)
        settings = nomic.new_page()
        settings.goto(f"http://127.0.0.1:{port}/admin")
        settings.wait_for_timeout(2500)
        want("microphone" in settings.text_content("#voice-check").lower()
             or "micro" in settings.text_content("#voice-check").lower(),
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
