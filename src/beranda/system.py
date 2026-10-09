"""What the Pi itself does for Beranda: screen hours, first-run help, updates, requests.

The web server never runs anything as root. When the settings page asks for an update, a
restart of the screen or a reboot, the server only drops a file named after the request in
the requests folder; a separate root service (beranda-actions, installed by install.sh)
carries it out. Only three names are understood.
"""

from __future__ import annotations

import os
import re
import socket
from datetime import UTC, datetime, time
from pathlib import Path

import httpx

from .config import Config

ACTIONS = ("update", "restart-screen", "reboot")
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


def lan_addresses(port: int) -> list[str]:
    """Addresses a phone on the same network can use, best first."""
    urls = []
    host = socket.gethostname()
    if host and host != "localhost":
        urls.append(f"http://{host}.local:{port}/admin")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # no packet is sent: this only picks the outgoing interface
            ip = s.getsockname()[0]
        if not ip.startswith("127."):
            urls.append(f"http://{ip}:{port}/admin")
    except OSError:
        pass
    return urls


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])
