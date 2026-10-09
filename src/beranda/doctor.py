"""`beranda doctor`: check everything Beranda needs and say, in plain words, what to fix."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

from . import __version__, config, system
from .providers import calendar_ics

OK, WARN, FAIL = "  ✓", "  !", "  ✗"
FONTS = {
    "Noto Sans CJK": "Chinese, Japanese, Korean",
    "Noto Sans Arabic": "Arabic, Persian, Urdu",
    "Noto Sans Devanagari": "Hindi",
    "Noto Sans Thai": "Thai",
    "Noto Sans Hebrew": "Hebrew",
    "Noto Sans Ethiopic": "Amharic",
}


def _fonts() -> list[str]:
    if not shutil.which("fc-list"):
        return [f"{WARN} cannot check the fonts (fc-list is missing)"]
    families = subprocess.run(["fc-list", ":", "family"], capture_output=True, text=True, check=False).stdout
    lines = []
    for family, used_for in FONTS.items():
        if family in families:
            lines.append(f"{OK} font {family} ({used_for})")
        else:
            lines.append(f"{WARN} font {family} missing: {used_for} will show as boxes. "
                         "Fix: sudo apt install fonts-noto-core fonts-noto-cjk")
    return lines


def _services() -> list[str]:
    if not shutil.which("systemctl"):
        return []
    lines = []
    for unit, what in (("beranda", "the server"), ("beranda-kiosk", "the full-screen display")):
        state = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, check=False).stdout.strip()
        if state == "active":
            lines.append(f"{OK} {what} is running ({unit})")
        elif state in {"inactive", "unknown", ""} and unit == "beranda-kiosk":
            lines.append(f"{WARN} {what} is not running. Normal if you installed with --no-screen.")
        else:
            lines.append(f"{FAIL} {what} is {state or 'not installed'}. See: journalctl -u {unit} -n 50")
    return lines


async def _network(cfg: config.Config) -> list[str]:
    lines = []
    async with httpx.AsyncClient(timeout=8) as client:
        try:
            r = await client.get(f"http://127.0.0.1:{cfg.port}/api/health")
            lines.append(f"{OK} the Beranda server answers on port {cfg.port} (version {r.json().get('version')})")
        except httpx.HTTPError:
            lines.append(f"{FAIL} nothing answers on port {cfg.port}. Start it: sudo systemctl start beranda")
        try:
            await client.get("https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current=temperature_2m")
            lines.append(f"{OK} internet works (weather service reachable)")
        except httpx.HTTPError:
            lines.append(f"{FAIL} no internet: the weather cannot load. Check the Wi-Fi of the Pi.")
    for index, url in enumerate(cfg.ics_urls):
        try:
            text = await calendar_ics.download(url)
            ok = "BEGIN:VCALENDAR" in text
            lines.append(f"{OK if ok else FAIL} calendar {index + 1} " + ("reads fine" if ok else "is not a calendar link"))
        except Exception as exc:  # noqa: BLE001 - never print the link: it is secret
            lines.append(f"{FAIL} calendar {index + 1} cannot be read ({type(exc).__name__}). "
                         "Copy the link again in the settings page.")
    return lines


def run() -> int:
    print(f"Beranda {__version__} — checking this computer\n")
    lines = []
    py = sys.version_info
    lines.append(f"{OK if py >= (3, 11) else FAIL} Python {py.major}.{py.minor}"
                 + ("" if py >= (3, 11) else ": Beranda needs 3.11 or newer"))
    path = config.find_config_path()
    cfg = config.Config()
    if path and Path(path).is_file():
        try:
            cfg = config.load(path)
            lines.append(f"{OK} settings read from {path}: {cfg.location.name}, {cfg.country}, "
                         f"language {cfg.language}, theme {cfg.theme}")
        except (OSError, ValueError) as exc:
            lines.append(f"{FAIL} the settings file {path} has a problem: {exc}")
    else:
        lines.append(f"{WARN} no settings saved yet: open the settings page and press Save")
    lines += _services()
    lines += asyncio.run(_network(cfg))
    lines += _fonts()
    info = system.install_info()
    if info:
        lines.append(f"{OK} installed with install.sh in {info.get('PREFIX')} (branch {info.get('BRANCH')}, {info.get('COMMIT')})")
    urls = system.lan_addresses(cfg.port)
    if urls:
        lines.append(f"{OK} settings page: " + "  or  ".join(urls))
    print("\n".join(lines))
    failed = any(line.startswith(FAIL) for line in lines)
    print("\nAll good." if not failed else "\nSome checks failed: see the ✗ lines above.")
    return 1 if failed else 0
