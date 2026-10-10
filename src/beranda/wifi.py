"""Wi-Fi from the settings page: see the network, keep several, add one, switch, forget.

The web server never runs as root and never touches the network. When the settings page asks
for something Wi-Fi, the server drops a small JSON "job" file in the requests folder; the root
helper (beranda-action) hands it to `beranda-wifi-job`, which is this module. It reads the job,
deletes it at once (it may hold a password), does it with `nmcli` (NetworkManager, the standard
network tool of Raspberry Pi OS), and writes the answer where the web server can read it.

Networks are saved by NetworkManager itself, so they survive reboots and even uninstalling
Beranda. Passwords stay with NetworkManager: never in Beranda's settings, never in a log, never
in an answer file.

Safety first, because the settings page usually reaches the Pi through that very Wi-Fi:
  - adding a network never cuts the current one (it is only remembered);
  - switching tries the new network for 45 seconds and goes back to the old one if it fails;
  - the network in use cannot be forgotten unless a cable is plugged in.
And if one day no known network is found at all, the "Beranda setup" safety net (wifi_setup.py)
opens its own Wi-Fi so a phone can pick a new one.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .wifi_setup import AP_CON_NAME, AP_SSID, scan

OPS = ("status", "scan", "add", "forget", "switch", "radio_on")
SWITCH_WAIT_SECONDS = 45
JOB_ID = re.compile(r"^[0-9a-f]{12}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class WifiError(Exception):
    """A plain reason the page can show (an English code it translates, see admin.js)."""


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, check=False, timeout=timeout)


def _terse(line: str) -> list[str]:
    """One line of `nmcli -t` output: fields split on ':', where nmcli writes a ':' inside a
    field as '\\:'."""
    return [part.replace("\\:", ":") for part in re.split(r"(?<!\\):", line)]


def why(result: subprocess.CompletedProcess, password: str = "") -> tuple[str, str]:
    """(code, detail) for a failed nmcli call: a code the page words in plain language, and
    nmcli's own last line for the diagnostic (never with the password in it)."""
    text = (result.stderr or result.stdout or "").strip()
    detail = text.splitlines()[-1] if text else ""
    if password:
        detail = detail.replace(password, "***")
    low = text.lower()
    if any(k in low for k in ("secrets were required", "802-1x supplicant", "psk", "wrong password", "invalid password")):
        code = "wrong_password"
    elif "no network with ssid" in low or "not found" in low:
        code = "not_found"
    elif any(k in low for k in ("radio", "rfkill", "wi-fi is disabled", "unavailable", "not available")):
        code = "radio_off"
    elif "timeout" in low or "timed out" in low:
        code = "timeout_connect"
    else:
        code = "switch_failed"
    return code, detail[:200]


def log(message: str) -> None:
    """One line in the system log (journalctl -u beranda-actions); never a password."""
    print(f"beranda-wifi-job: {message}", file=sys.stderr, flush=True)


# ------------------------------------------------------------------ checks ---
def check_ssid(ssid: object) -> str:
    if not isinstance(ssid, str) or not ssid or len(ssid.encode()) > 32 or _CONTROL.search(ssid):
        raise WifiError("bad_name")
    return ssid


def check_password(password: object) -> str:
    """'' (an open network), 8 to 63 characters (WPA), or 64 hexadecimal digits."""
    if password in (None, ""):
        return ""
    if not isinstance(password, str) or _CONTROL.search(password):
        raise WifiError("bad_password")
    if 8 <= len(password) <= 63 or re.fullmatch(r"[0-9a-fA-F]{64}", password):
        return password
    raise WifiError("bad_password")


# ------------------------------------------------------------------ reading ---
def saved() -> list[dict]:
    """The Wi-Fi networks this Pi knows (NetworkManager profiles), never the setup network."""
    out = _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).stdout
    networks = []
    for line in out.splitlines():
        parts = _terse(line)
        if len(parts) >= 2 and parts[1] == "802-11-wireless" and parts[0] != AP_CON_NAME:
            ssid = _run(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", "id", parts[0]]).stdout.strip()
            networks.append({"name": parts[0], "ssid": ssid or parts[0]})
    return networks


def status() -> dict:
    """Which network is in use, how strong, the Pi's address, and whether a cable is plugged in."""
    wifi = {"device": "", "connection": "", "ssid": "", "signal": None}
    wifi_state = ""
    ethernet = False
    for line in _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"]).stdout.splitlines():
        parts = _terse(line)
        if len(parts) < 4:
            continue
        device, kind, state, connection = parts[:4]
        if kind == "wifi" and not wifi["device"]:
            wifi["device"] = device
            wifi_state = state
            if state.startswith("connected"):
                wifi["connection"] = connection
        elif kind == "ethernet" and state.startswith("connected"):
            ethernet = True
    for line in _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "device", "wifi", "list", "--rescan", "no"]).stdout.splitlines():
        parts = _terse(line)
        if len(parts) >= 3 and parts[0] == "yes":
            wifi["ssid"] = parts[1]
            wifi["signal"] = int(parts[2]) if parts[2].isdigit() else None
            break
    address = ""
    if wifi["device"]:
        for line in _run(["nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", wifi["device"]]).stdout.splitlines():
            if ":" in line:
                address = line.split(":", 1)[1].split("/")[0]
                break
    net = _run(["systemctl", "is-enabled", "beranda-wifi-setup.service"]).stdout.strip()
    radio = _run(["nmcli", "radio", "wifi"]).stdout.strip()
    return {
        "radio": radio != "disabled",
        "wifi_state": wifi_state,
        "available": bool(wifi["device"]),
        "connection": wifi["connection"] if wifi["connection"] != AP_CON_NAME else "",
        "setup_hotspot": wifi["connection"] == AP_CON_NAME,
        "ssid": wifi["ssid"] if wifi["connection"] != AP_CON_NAME else "",
        "signal": wifi["signal"],
        "address": address,
        "ethernet": ethernet,
        "saved": saved(),
        "safety_net": net == "enabled",
    }


# ------------------------------------------------------------------ changing ---
def add(ssid: str, password: str, hidden: bool = False) -> dict:
    """Remember a network (or give a known one its new password). Never disconnects anything."""
    ssid, password = check_ssid(ssid), check_password(password)
    if ssid == AP_SSID:
        raise WifiError("bad_name")
    known = next((n for n in saved() if n["ssid"] == ssid), None)
    if known:
        name = known["name"]
        args = ["nmcli", "connection", "modify", "id", name, "connection.autoconnect", "yes",
                "802-11-wireless.hidden", "yes" if hidden else "no"]
    else:
        name = ssid
        args = ["nmcli", "connection", "add", "type", "wifi", "ifname", "*", "con-name", name, "ssid", ssid,
                "connection.autoconnect", "yes", "802-11-wireless.hidden", "yes" if hidden else "no"]
    if password:
        args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    elif not known:
        pass  # an open network: no security section at all
    result = _run(args)
    if result.returncode != 0:
        _code, detail = why(result, password)
        log(f"saving {ssid!r} failed: {detail}")
        return {"ok": False, "error": "not_saved", "detail": detail}
    log(f"saved {ssid!r}")
    return {"ok": True, "name": name, "updated": bool(known)}


def forget(name: str) -> dict:
    """Forget a saved network. The one in use stays, unless a cable keeps the Pi reachable."""
    current = status()
    if name not in {n["name"] for n in current["saved"]}:
        raise WifiError("unknown_network")
    if name == current["connection"] and not current["ethernet"]:
        raise WifiError("in_use")
    if _run(["nmcli", "connection", "delete", "id", name]).returncode != 0:
        raise WifiError("not_forgotten")
    return {"ok": True, "name": name}


def switch(name: str) -> dict:
    """Use another saved network now. If it does not work within 45 seconds, go back to the
    one that worked, so the Pi never stays cut off."""
    current = status()
    if name not in {n["name"] for n in current["saved"]}:
        raise WifiError("unknown_network")
    previous = current["connection"]
    if name == previous:
        return {"ok": True, "name": name, "same": True}
    result = _run(["nmcli", "--wait", str(SWITCH_WAIT_SECONDS), "connection", "up", "id", name],
                  timeout=SWITCH_WAIT_SECONDS + 15)
    if result.returncode == 0:
        log(f"now on {name!r}")
        return {"ok": True, "name": name}
    code, detail = why(result)
    log(f"could not use {name!r} ({code}): {detail}")
    back = False
    if previous:
        back = _run(["nmcli", "--wait", "30", "connection", "up", "id", previous], timeout=45).returncode == 0
    return {"ok": False, "name": name, "error": code, "detail": detail, "back_to": previous if back else "",
            "ethernet": current["ethernet"]}


def radio_on(country: str = "") -> dict:
    """Turn the Wi-Fi radio on. On Raspberry Pi OS it stays off until a Wi-Fi country is set
    (a legal requirement): set it from Beranda's own country when none is set yet."""
    done = []
    if country and re.fullmatch(r"[A-Z]{2}", country) and shutil.which("raspi-config"):
        current = _run(["raspi-config", "nonint", "get_wifi_country"]).stdout.strip()
        if not re.fullmatch(r"[A-Z]{2}", current or "") and \
                _run(["raspi-config", "nonint", "do_wifi_country", country]).returncode == 0:
            done.append(f"country {country}")
    if shutil.which("rfkill"):
        _run(["rfkill", "unblock", "wifi"])
    result = _run(["nmcli", "radio", "wifi", "on"])
    if result.returncode != 0:
        _code, detail = why(result)
        log(f"could not turn the Wi-Fi on: {detail}")
        return {"ok": False, "error": "radio_off", "detail": detail}
    log("Wi-Fi turned on" + (f" ({', '.join(done)})" if done else ""))
    return {"ok": True, "country_set": bool(done)}


def networks_around() -> dict:
    known = {n["ssid"] for n in saved()}
    return {"networks": [{"ssid": n.ssid, "signal": n.signal, "secured": n.secured, "saved": n.ssid in known}
                         for n in scan()]}


def run_job(job: dict) -> dict:
    op = job.get("op")
    if op not in OPS:
        raise WifiError("unknown_op")
    if op == "status":
        return status()
    if op == "scan":
        return networks_around()
    if op == "add":
        return add(job.get("ssid"), job.get("password", ""), bool(job.get("hidden")))
    if op == "radio_on":
        return radio_on(str(job.get("country", "")).upper())
    name = job.get("name")
    if not isinstance(name, str) or not name:
        raise WifiError("unknown_network")
    return forget(name) if op == "forget" else switch(name)


# ------------------------------------------------------------------ the job files ---
def results_dir() -> Path:
    return Path(os.environ.get("BERANDA_WIFI_JOBS", "/var/lib/beranda/wifi-jobs"))


def _write_result(folder: Path, job_id: str, result: dict, owner: tuple[int, int] | None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f".{job_id}.tmp"
    tmp.write_text(json.dumps(result))
    os.chmod(tmp, 0o640)
    if owner:
        os.chown(tmp, *owner)
    os.replace(tmp, folder / f"{job_id}.json")
    # answers older than an hour are of no use to anybody
    for old in folder.glob("*.json"):
        try:
            if time.time() - old.stat().st_mtime > 3600:
                old.unlink()
        except OSError:
            pass


def job_main(argv: list[str] | None = None) -> int:
    """`beranda-wifi-job REQUEST_FILE`: run as root by beranda-action."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: beranda-wifi-job REQUEST_FILE", file=sys.stderr)
        return 2
    request = Path(args[0])
    job_id = request.stem.removeprefix("wifi-")
    if not JOB_ID.match(job_id):
        request.unlink(missing_ok=True)
        return 2
    folder = results_dir()
    try:
        stat = request.stat()
        owner = (stat.st_uid, stat.st_gid)  # the web server's user: it must read the answer
        job = json.loads(request.read_text())
    except (OSError, ValueError):
        job, owner = {}, None
    request.unlink(missing_ok=True)  # at once: it may hold a password
    try:
        result = run_job(job if isinstance(job, dict) else {})
    except WifiError as exc:
        result = {"ok": False, "error": str(exc)}
    except (OSError, subprocess.SubprocessError) as exc:
        result = {"ok": False, "error": "nmcli_missing" if isinstance(exc, FileNotFoundError) else "failed"}
    result["done"] = True
    try:
        _write_result(folder, job_id, result, owner)
    except OSError:
        return 1
    return 0


def new_job_id() -> str:
    return secrets.token_hex(6)
