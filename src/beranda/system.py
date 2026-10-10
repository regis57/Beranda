"""What the Pi itself does for Beranda: screen hours, first-run help, updates, requests.

The web server never runs anything as root. When the settings page asks for an update, a
restart of the screen or a reboot, the server only drops a file named after the request in
the requests folder; a separate root service (beranda-actions, installed by install.sh)
carries it out. Only four names are understood.
"""

from __future__ import annotations

import json
import os
import re
import signal
import socket
from datetime import UTC, datetime, time
from pathlib import Path

import httpx

from .config import Config

ACTIONS = ("update", "restart-screen", "reboot", "reset")

DEFAULT_PORT = 8080
# A program that is not root may only listen on ports from 1024 up (Beranda never runs as root).
PORT_MIN, PORT_MAX = 1024, 65535
RAW_VERSION_URL = "https://raw.githubusercontent.com/regis57/Beranda/{branch}/src/beranda/__init__.py"


def _parse_hhmm(text: str) -> time | None:
    if not text:
        return None
    hours, minutes = text.split(":")
    return time(int(hours), int(minutes))


def screen_should_be_on(cfg: Config, now: datetime) -> bool:
    """False between the "off" and "on" hours, even across midnight (23:00 -> 06:30)."""
    off, on = _parse_hhmm(cfg.screen_off), _parse_hhmm(cfg.screen_on)
    if off is None or on is None or off == on:
        return True
    current = now.time()
    if off < on:  # e.g. off 01:00, on 06:00
        return not (off <= current < on)
    return on <= current < off  # e.g. off 23:00, on 06:30


def install_info() -> dict[str, str]:
    """What install.sh wrote; empty when Beranda was not installed with it."""
    path = Path(os.environ.get("BERANDA_INSTALL_INFO", "/etc/beranda/install.env"))
    info: dict[str, str] = {}
    try:
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.startswith("#"):
                info[key.strip()] = value.strip()
    except OSError:
        pass
    return info


def requests_dir() -> Path | None:
    raw = os.environ.get("BERANDA_REQUESTS")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_dir() and os.access(path, os.W_OK) else None


def wifi_setup_status() -> dict | None:
    """What the optional beranda-wifi-setup service wrote: the open setup network's name, while
    it is up. None once a real connection exists (the file is removed) or the service was never
    installed at all."""
    raw = os.environ.get("BERANDA_WIFI_STATUS", "/var/lib/beranda/wifi-setup.json")
    try:
        return json.loads(Path(raw).read_text())
    except (OSError, ValueError):
        return None


def helper_state() -> str:
    """"busy" (beranda-actions is running something), "stuck" (failed, or its watcher stopped),
    "ok", or "unknown" (no systemd here)."""
    import shutil
    import subprocess

    if not shutil.which("systemctl"):
        return "unknown"

    def state(unit: str) -> str:
        try:
            return subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True,
                                  timeout=5, check=False).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return "unknown"

    service, watcher = state("beranda-actions.service"), state("beranda-actions.path")
    if service in ("activating", "active", "reloading"):
        return "busy"
    if service == "failed" or watcher in ("failed", "inactive"):
        return "stuck"
    return "ok" if watcher == "active" else "unknown"


def request_action(action: str) -> None:
    if action not in ACTIONS:
        raise ValueError(f"unknown action {action!r}")
    folder = requests_dir()
    if folder is None:
        raise RuntimeError("not installed with install.sh")
    (folder / action).write_text(datetime.now(UTC).isoformat())


async def latest_version(branch: str = "main") -> str | None:
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            r = await client.get(RAW_VERSION_URL.format(branch=branch))
            r.raise_for_status()
    except httpx.HTTPError:
        return None
    match = re.search(r'__version__\s*=\s*"([^"]+)"', r.text)
    return match.group(1) if match else None


def port_is_free(host: str, port: int) -> bool:
    """True when nothing is listening on that port yet (we try to take it, then let go)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host or "0.0.0.0", port))
        except OSError:
            return False
    return True


def port_problem(port: object, current: int, host: str = "0.0.0.0") -> str | None:
    """Why this port cannot be used, as a short code the settings page translates; None if fine.
    Codes: "range" (not a number from 1024 to 65535), "same" (already the one in use) and
    "busy" (another program is listening there)."""
    if isinstance(port, bool) or not isinstance(port, int) or not PORT_MIN <= port <= PORT_MAX:
        return "range"
    if port == current:
        return "same"
    return None if port_is_free(host, port) else "busy"


def runs_under_systemd() -> bool:
    """True when systemd started us (it sets INVOCATION_ID) and will start us again if we stop."""
    return bool(os.environ.get("INVOCATION_ID")) and bool(install_info())


def restart_server_soon(delay: float = 1.5) -> bool:
    """Stop this server a moment from now so systemd starts it again with the new settings
    (the answer to the settings page goes out first). Returns False, and does nothing, when
    nothing would start it again - for instance when you run `beranda` by hand."""
    if not runs_under_systemd():
        return False
    import asyncio

    asyncio.get_running_loop().call_later(delay, os.kill, os.getpid(), signal.SIGTERM)
    return True


def lan_addresses(port: int) -> list[str]:
    """Addresses a phone on the same network can use, best first."""
    from .tls import lan_ip

    urls = []
    host = socket.gethostname()
    if host and host != "localhost":
        urls.append(f"http://{host}.local:{port}/admin")
    ip = lan_ip()
    if ip:
        urls.append(f"http://{ip}:{port}/admin")
    return urls


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])
