"""Wi-Fi setup with no keyboard and no monitor cable: if the Pi boots with no network at all
(a blank SD card, no Ethernet plugged in), it briefly becomes its own Wi-Fi access point named
"Beranda setup" so you can join it from a phone or laptop, pick your home Wi-Fi from one small
page, and never touch a terminal.

Like the voice service, this is a *second*, optional, root-only process (its own systemd
service, installed only with `install.sh --with-wifi-setup`) - the main Beranda web server
never runs as root and never touches the network itself (see system.py). Everything below is
plain glue around the `nmcli` command (NetworkManager, the default on Raspberry Pi OS Bookworm
and newer), so it is fully testable without any real Wi-Fi hardware; only `main()` actually
puts the radio into access-point mode and could not be tried on a real Raspberry Pi from this
development environment - expect to tune it once you can.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time as time_mod
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# The access point's name and the (fixed, root-owned) NetworkManager connection it lives under.
AP_SSID = "Beranda setup"
AP_CON_NAME = "beranda-setup-ap"
# NetworkManager's own default address for a "shared" connection - what phones get once they join.
AP_IP = "10.42.0.1"
# A drop-in that makes every address a captive-portal check asks for resolve back to the Pi
# itself, so phones open the setup page on their own instead of showing "no internet".
DNSMASQ_DROPIN = Path("/etc/NetworkManager/dnsmasq-shared.d/beranda-captive.conf")
# Where the main web server learns whether the hotspot is up right now (see write_status below).
STATUS_FILE_ENV = "BERANDA_WIFI_STATUS"
DEFAULT_STATUS_FILE = Path("/var/lib/beranda/wifi-setup.json")
# How long with no connection at all before the "Beranda setup" network opens: short on a Pi
# that knows no Wi-Fi yet (first start), longer once it knows one (a box restarting takes a
# minute or two, and must not be mistaken for a lost network).
CONNECT_GRACE_SECONDS = 45
LOST_GRACE_SECONDS = 2 * 60
POLL_SECONDS = 3
CHECK_SECONDS = 15  # while connected, a look every 15 s is plenty
# How long the setup network stays open before Beranda closes it and tries the known networks
# again (one radio cannot do both at once): long for a first setup, short when known networks
# exist, so the Pi comes back by itself as soon as the usual Wi-Fi is back.
AP_TIMEOUT_SECONDS = 15 * 60
AP_RETRY_SECONDS = 5 * 60


def status_file() -> Path:
    return Path(os.environ.get(STATUS_FILE_ENV, DEFAULT_STATUS_FILE))


@dataclass
class Network:
    """One Wi-Fi network seen during a scan, as shown in the pick list."""

    ssid: str
    signal: int  # 0-100, nmcli's own scale
    secured: bool


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def knows_a_wifi() -> bool:
    """True when at least one Wi-Fi network is saved (not counting the setup network)."""
    out = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).stdout
    return any(
        line.endswith(":802-11-wireless") and not line.startswith(f"{AP_CON_NAME}:") for line in out.splitlines()
    )


def is_connected() -> bool:
    """True once the Pi has any working connection at all (Wi-Fi or Ethernet)."""
    state = _run(["nmcli", "-t", "-f", "STATE", "general", "status"]).stdout.strip()
    return state.startswith("connected")


_UNESCAPED_COLON = re.compile(r"(?<!\\):")


def _split_terse(line: str) -> list[str]:
    """Split one line of `nmcli -t` output on ':', except where nmcli itself escaped a ':'
    inside a field (as '\\:') because the field's own text contained one."""
    return [part.replace("\\:", ":") for part in _UNESCAPED_COLON.split(line)]


def scan() -> list[Network]:
    """Wi-Fi networks in range right now, strongest first, one entry per name (no duplicates
    for the same network seen on several channels, and never the setup network itself)."""
    out = _run(
        ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "yes"]
    ).stdout
    best: dict[str, Network] = {}
    for line in out.splitlines():
        parts = _split_terse(line)
        if len(parts) < 3:
            continue
        ssid = parts[0]
        if not ssid or ssid == AP_SSID:
            continue
        try:
            signal = int(parts[1])
        except ValueError:
            signal = 0
        secured = parts[2].strip() not in ("", "--")
        existing = best.get(ssid)
        if existing is None or signal > existing.signal:
            best[ssid] = Network(ssid=ssid, signal=signal, secured=secured)
    return sorted(best.values(), key=lambda n: n.signal, reverse=True)


def connect(ssid: str, password: str) -> tuple[bool, str]:
    """Try to join `ssid`. Never logs or returns the password, success or not."""
    if not ssid:
        return False, "no network name given"
    args = ["nmcli", "device", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    result = _run(args)
    if result.returncode == 0:
        return True, "connected"
    lines = [line.strip() for line in (result.stderr or result.stdout or "").splitlines() if line.strip()]
    return False, (lines[-1] if lines else "could not connect")


def start_hotspot() -> None:
    """Turn the Pi's own Wi-Fi radio into an open access point so a phone or laptop can join it
    with no password and reach the setup page. It is only ever open during this short setup
    window - once a real connection is made (or the Pi already has one), it is torn down."""
    _run(["nmcli", "connection", "delete", AP_CON_NAME])  # ignore failure: may not exist yet
    _run([
        "nmcli", "connection", "add", "type", "wifi", "ifname", "*", "con-name", AP_CON_NAME,
        "autoconnect", "no", "ssid", AP_SSID,
        "mode", "ap", "ipv4.method", "shared",
        "wifi-sec.key-mgmt", "none",
    ])
    try:
        DNSMASQ_DROPIN.parent.mkdir(parents=True, exist_ok=True)
        DNSMASQ_DROPIN.write_text(
            "# Written by Beranda while its Wi-Fi setup hotspot is up: answer every address a\n"
            "# phone's captive-portal check asks for with the Pi's own address, so it opens the\n"
            "# setup page by itself instead of just saying \"no internet\".\n"
            f"address=/#/{AP_IP}\n"
        )
    except OSError:
        log.warning("could not write %s; the setup page still works once opened by hand", DNSMASQ_DROPIN)
    _run(["nmcli", "connection", "up", AP_CON_NAME])
    write_status(AP_SSID)


def stop_hotspot() -> None:
    _run(["nmcli", "connection", "down", AP_CON_NAME])
    _run(["nmcli", "connection", "delete", AP_CON_NAME])
    try:
        DNSMASQ_DROPIN.unlink(missing_ok=True)
    except OSError:
        pass
    write_status(None)


def write_status(ssid: str | None) -> None:
    """Tell the main Beranda server whether the setup hotspot is up, so the kiosk screen can
    show "join Wi-Fi '...' to finish setup" with a QR code. A small JSON file, not a direct
    call, because the web server never runs as root and never touches the network itself."""
    path = status_file()
    try:
        if ssid:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"ssid": ssid, "open": True}))
            path.chmod(0o644)  # this service runs as root; the web server (another user) must read it
        else:
            path.unlink(missing_ok=True)
    except OSError:
        log.warning("could not update %s", path)


# -------------------------------------------------------------------- the setup page -----

PORTAL_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Beranda - Wi-Fi setup</title>
<style>
  body { font-family: system-ui, sans-serif; background: #111; color: #eee; margin: 0;
         padding: 24px 16px 48px; display: flex; flex-direction: column; align-items: center; }
  h1 { font-size: 1.4rem; text-align: center; }
  p { color: #bbb; text-align: center; max-width: 28em; }
  form { width: 100%; max-width: 22em; }
  select, input, button { width: 100%; box-sizing: border-box; font-size: 1.1rem; padding: 12px;
                           margin: 6px 0; border-radius: 10px; border: 1px solid #444; }
  select, input { background: #1c1c1c; color: #eee; }
  button { background: #2e7d32; color: #fff; border: none; font-weight: 600; }
  button:disabled { background: #444; }
  #message { min-height: 1.4em; text-align: center; }
  #message.error { color: #ff8a80; }
  #message.ok { color: #a5d6a7; }
</style>
</head>
<body>
  <h1>Connect Beranda to your Wi-Fi</h1>
  <p>Pick your home Wi-Fi network below and enter its password. Beranda will join it and this
  page will stop working once it does - that is normal, it means it worked.</p>
  <form id="form">
    <select id="ssid"><option value="">Scanning for networks...</option></select>
    <input id="password" type="password" placeholder="Wi-Fi password" autocomplete="off">
    <button id="submit" type="submit">Connect</button>
  </form>
  <p id="message"></p>
  <script>
    const form = document.getElementById('form');
    const ssidField = document.getElementById('ssid');
    const message = document.getElementById('message');
    const submitButton = document.getElementById('submit');

    async function loadNetworks() {
      try {
        const res = await fetch('/api/networks');
        const data = await res.json();
        ssidField.replaceChildren();
        if (!data.networks.length) {
          ssidField.append(new Option('No network found - move closer and reload', ''));
          return;
        }
        for (const n of data.networks) {
          ssidField.append(new Option(n.ssid + (n.secured ? ' (needs a password)' : ' (open)'), n.ssid));
        }
      } catch {
        ssidField.replaceChildren(new Option('Could not scan - reload this page', ''));
      }
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const ssid = ssidField.value;
      if (!ssid) return;
      submitButton.disabled = true;
      message.className = '';
      message.textContent = 'Connecting...';
      try {
        const res = await fetch('/api/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ssid, password: document.getElementById('password').value }),
        });
        const data = await res.json();
        if (data.ok) {
          message.className = 'ok';
          message.textContent = 'Connected! You can close this page.';
        } else {
          message.className = 'error';
          message.textContent = 'Could not connect: ' + data.message;
          submitButton.disabled = false;
        }
      } catch {
        message.className = 'error';
        message.textContent = 'Could not reach Beranda - stay on this Wi-Fi and try again.';
        submitButton.disabled = false;
      }
    });

    loadNetworks();
  </script>
</body>
</html>"""


def create_portal_app():
    """A tiny, self-contained FastAPI app: the setup page itself, plus the handful of URLs
    phones and computers probe right after joining a new Wi-Fi network to decide whether to
    pop the page open on their own ("captive portal" detection)."""
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

    app = FastAPI(title="Beranda Wi-Fi setup", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return PORTAL_PAGE

    @app.get("/api/networks")
    async def networks() -> dict:
        return {"networks": [asdict(n) for n in scan()]}

    @app.post("/api/connect")
    async def do_connect(body: dict) -> dict:
        ssid = (body.get("ssid") or "").strip()
        password = body.get("password") or ""
        ok, message = connect(ssid, password)
        return {"ok": ok, "message": message}

    # Most phones and computers fetch one of the URLs below right after joining a new network;
    # answering with a redirect to our own page (instead of what a real site would answer) is
    # what makes the setup page pop open on its own, with nothing for anyone to type or tap.
    async def _probe() -> RedirectResponse:
        return RedirectResponse("/")

    for path in ("/generate_204", "/gen_204", "/hotspot-detect.html", "/connecttest.txt", "/ncsi.txt"):
        app.get(path)(_probe)

    @app.get("/{anything:path}")
    async def catch_all(anything: str) -> JSONResponse | RedirectResponse:
        # Anything else (a phone probing some other address entirely) still lands on the page.
        return RedirectResponse("/")

    return app


# -------------------------------------------------------------------- the real-hardware loop ---


def grace_seconds() -> int:
    return LOST_GRACE_SECONDS if knows_a_wifi() else CONNECT_GRACE_SECONDS


def open_seconds() -> int:
    return AP_RETRY_SECONDS if knows_a_wifi() else AP_TIMEOUT_SECONDS


def main() -> None:  # pragma: no cover - needs a real Wi-Fi radio
    """The safety net, always running: watches the connection, and when there has been none
    for a while (2 minutes once a Wi-Fi is known, 45 seconds on a first start), opens the
    "Beranda setup" network with its one-page Wi-Fi picker. It closes it once a connection
    exists, or after a while to let the Pi try its known networks again, and keeps watching.
    """
    import threading

    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s wifi-setup: %(message)s")
    write_status(None)
    while True:
        lost = 0
        while lost < grace_seconds():
            if is_connected():
                lost = 0
                time_mod.sleep(CHECK_SECONDS)
            else:
                time_mod.sleep(POLL_SECONDS)
                lost += POLL_SECONDS
        log.info("no network for %ss; opening the setup network %r", lost, AP_SSID)
        start_hotspot()
        server = uvicorn.Server(uvicorn.Config(create_portal_app(), host="0.0.0.0", port=80, log_level="warning"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            waited, limit = 0, open_seconds()
            while waited < limit:
                if is_connected() and not _hotspot_only():
                    log.info("connected; closing the setup network")
                    break
                time_mod.sleep(POLL_SECONDS)
                waited += POLL_SECONDS
            else:
                log.info("nobody used the setup network; trying the known networks again")
        finally:
            server.should_exit = True
            thread.join(5)
            stop_hotspot()


def _hotspot_only() -> bool:
    """While the setup network is up, NetworkManager calls the Pi "connected" (to itself)."""
    out = _run(["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"]).stdout.split()
    return out == [AP_CON_NAME]


if __name__ == "__main__":
    sys.exit(main())
