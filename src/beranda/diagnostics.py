"""A diagnostic file to attach to a bug report: what Beranda is, what it is set to, how the
device is doing and what went wrong lately, in plain text.

It never contains a secret: no calendar link, no Dropbox link, no feed address, no PIN, no
Wi-Fi password, no full web address (only the site name), and the place is rounded to about
10 km. The person downloads the file and decides who to send it to.
"""

from __future__ import annotations

import collections
import logging
import os
import platform
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from . import __version__, limits, system
from .config import Config

START = time.time()
SERVICES = ("beranda", "beranda-kiosk", "beranda-actions.path", "beranda-wifi-setup")


# ------------------------------------------------------------------ recent log lines ---
class LogBuffer(logging.Handler):
    """Keeps the last few log lines in memory (with every web address cut down to its site name)."""

    def __init__(self, size: int = 300) -> None:
        super().__init__(level=logging.INFO)
        self.lines: collections.deque[str] = collections.deque(maxlen=size)
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.lines.append(scrub(self.format(record))[:400])
        except Exception:  # noqa: BLE001 - logging must never break the program
            self.handleError(record)


_buffer: LogBuffer | None = None


def install_log_buffer() -> LogBuffer:
    """Start keeping Beranda's own log lines (once, however many times the app is created)."""
    global _buffer
    if _buffer is None:
        _buffer = LogBuffer()
        logging.getLogger("beranda").addHandler(_buffer)
    return _buffer


_URL = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)


def scrub(text: str) -> str:
    """Every web address becomes just its site name: paths and query strings can hold secrets."""
    return _URL.sub(lambda m: f"{urlparse(m.group(0)).scheme}://{urlparse(m.group(0)).hostname or '?'}/…", text)


def site(url: str) -> str:
    """Only the site name of an address ('' when there is none)."""
    return (urlparse(url.strip()).hostname or "?") if url.strip() else ""


# ------------------------------------------------------------------ what the screens tell ---
# The display page (the mirror, a tablet...) reports what goes wrong there, such as a microphone
# that cannot be used, so the diagnostic file made from the settings page can show it too.
_display: collections.deque[str] = collections.deque(maxlen=40)


def note_display(event: str, browser: str) -> None:
    when = datetime.now().astimezone().strftime("%H:%M:%S")
    _display.append(f"{when} {scrub(event)[:200]}   [{_short_browser(browser)}]")


def _short_browser(agent: str) -> str:
    """'Edge 154 on Windows' rather than the whole user-agent line."""
    agent = agent or ""
    for name, mark in (("Edge", "Edg/"), ("Opera", "OPR/"), ("Samsung", "SamsungBrowser/"), ("Firefox", "Firefox/"),
                       ("Chrome", "Chrome/"), ("Safari", "Version/")):
        if mark in agent:
            version = agent.split(mark, 1)[1].split(".", 1)[0]
            break
    else:
        name, version = "browser", "?"
    system_name = next((s for s, m in (("Windows", "Windows"), ("Android", "Android"), ("iPad", "iPad"), ("iPhone", "iPhone"),
                                       ("macOS", "Mac OS"), ("Linux", "Linux")) if m in agent), "?")
    return f"{name} {version} on {system_name}"


def display_lines() -> list[str]:
    return list(_display) or ["nothing reported"]


# ------------------------------------------------------------------ the device ---
def _read(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return ""


def _service_state(name: str) -> str:
    try:
        done = subprocess.run(
            ["systemctl", "is-active", name], capture_output=True, text=True, timeout=3, check=False
        )
        return done.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def device_lines() -> list[str]:
    model, ram = limits.device()
    meminfo = _read("/proc/meminfo")
    free = re.search(r"MemAvailable:\s+(\d+)", meminfo)
    temp = _read("/sys/class/thermal/thermal_zone0/temp")
    uptime = _read("/proc/uptime").split(" ")[0]
    try:
        disk = shutil.disk_usage("/")
        disk_text = f"{disk.free // 2**20} MB free of {disk.total // 2**20} MB"
    except OSError:
        disk_text = "?"
    out = [
        f"board: {model.strip(chr(0)) or 'not a Raspberry Pi'}",
        f"memory: {ram} GB (about {int(free.group(1)) // 1024} MB free)" if free else f"memory: {ram} GB",
        f"cpu temperature: {int(temp) / 1000:.0f} C" if temp.isdigit() else "cpu temperature: ?",
        f"device up for: {int(float(uptime)) // 3600} h" if uptime else "device up for: ?",
        f"load average: {', '.join(f'{x:.2f}' for x in os.getloadavg())}" if hasattr(os, "getloadavg") else "",
        f"disk: {disk_text}",
        f"system: {platform.system()} {platform.release()} {platform.machine()}",
        f"python: {platform.python_version()}",
    ]
    if shutil.which("systemctl"):
        out.append("services: " + ", ".join(f"{name}={_service_state(name)}" for name in SERVICES))
    return [line for line in out if line]


# ------------------------------------------------------------------ the settings ---
def settings_lines(cfg: Config, photo_folder: Path, own_photos: int, shown_photos: int) -> list[str]:
    loc = cfg.location
    cap = cfg.limits
    names = ", ".join(n for _id, n in cfg.tv_channel_names)
    feeds = len(cfg.news_feeds)
    news_sources = "automatic" if cfg.news_sources is None else ", ".join(cfg.news_sources) or "none"
    return [
        "[look]",
        f"language: {cfg.language}   country: {cfg.country}   region: {cfg.subdivision or '-'}   units: {cfg.units}",
        f"theme: {cfg.theme}   mode: {cfg.mode}   week starts on: {'Sunday' if cfg.week_start == 6 else 'Monday'}",
        f"screen: rotate {cfg.screen_rotate}, off {cfg.screen_off or '-'}, on {cfg.screen_on or '-'}",
        "",
        "[place] (rounded to about 10 km)",
        f"town: {loc.name}   time zone: {loc.timezone}   at: {loc.latitude:.1f}, {loc.longitude:.1f}",
        "",
        "[extras of the main screen]",
        f"24 h graph: {cfg.widget_chart}   air/UV/pollen: {cfg.widget_air}   ephemeris: {cfg.widget_ephemeris}",
        f"weather warnings: {cfg.widget_alerts} (area: {cfg.alerts_area or '-'})   second clock: {cfg.second_clock or 'off'}",
        "",
        "[content]",
        f"calendars: {len(cfg.ics_urls)} link(s), not shown   key dates: {len(cfg.key_dates)}",
        f"news: {'on' if cfg.news_enabled else 'off'}, sources: {news_sources}, own feeds: {feeds}   history: {cfg.history_enabled}",
        (f"photos: {'own folder' if not cfg.photos_folder.strip() else 'a folder chosen by hand'}, "
        f"{own_photos} in Beranda's folder, {shown_photos} shown, every {cfg.photos_interval} s, "
        f"Dropbox link: {'yes' if cfg.photos_dropbox_url else 'no'}   (folder: {photo_folder.name})"),
        f"radio: {len(cfg.radio_stations)} favourite(s): {', '.join(s.name for s in cfg.radio_stations) or '-'}   volume: {cfg.radio_volume}",
        f"tv: guide site {site(cfg.tv_xmltv_url) or '-'}, {len(cfg.tv_channels)} channel(s): {names or ', '.join(cfg.tv_channels) or '-'}",
        f"voice: {'on' if cfg.voice_enabled else 'off'}, own phrases: {len(cfg.voice_commands)}",
        f"settings PIN: {'set' if cfg.admin_pin else 'not set'}",
        "",
        "[limits]",
        (f"profile: {cap.profile} (calendars {len(cfg.ics_urls)}/{cap.calendars}, news sources "
        f"{len(cfg.news_feeds) + len(cfg.news_sources or ())}/{cap.news_sources}, tv {len(cfg.tv_channels)}/{cap.tv_channels}, "
        f"radio {len(cfg.radio_stations)}/{cap.radio_stations}, dates {len(cfg.key_dates)}/{cap.key_dates}, "
        f"voice phrases {len(cfg.voice_commands)}/{cap.voice_commands})"),
    ]


def state_lines(state: dict | None, problem: str = "") -> list[str]:
    """What the display is showing right now, boiled down to what helps find a problem."""
    if not state:
        return [f"could not be read: {problem or 'unknown reason'}"]
    weather = state.get("weather") or {}
    tv = state.get("tv") or {}
    alerts = state.get("alerts") or {}
    air = state.get("air") or {}
    return [
        f"generated at: {state.get('generated_at')}   mode shown: {state.get('mode')}   demo: {state.get('demo')}",
        (f"weather: {'ok' if weather else 'MISSING'}   agenda events: {len(state.get('events') or [])}   "
        f"special days: {len(state.get('special_days') or [])}   news headlines: {len((state.get('news') or {}).get('items', []) if isinstance(state.get('news'), dict) else state.get('news') or [])}"),
        (f"photos: {len((state.get('photos') or {}).get('names', []))}   radio stations: {len((state.get('radio') or {}).get('stations', []))}   "
        f"tv: {tv.get('status', '-')} ({len(tv.get('programmes') or [])} programme(s))"),
        (f"air: {air.get('status', 'on' if air else 'off/none')}   warnings: {alerts.get('status', 'off/none')} "
        f"({len(alerts.get('items') or [])} item(s))   history: {'ok' if state.get('history') else 'none'}"),
        f"stale (old data shown because the network failed): {', '.join(state.get('stale') or []) or 'none'}",
        f"errors: {', '.join(f'{k}={v}' for k, v in (state.get('errors') or {}).items()) or 'none'}",
    ]


# ------------------------------------------------------------------ what the browser sent ---
def client_lines(client: dict) -> list[str]:
    def short(key: str, size: int = 200) -> str:
        return scrub(str(client.get(key, "?")))[:size]

    lines = [
        f"browser: {short('user_agent')}",
        f"language: {short('language', 40)}   time zone: {short('time_zone', 60)}   colour scheme: {short('scheme', 20)}",
        f"screen: {short('screen', 30)}   window: {short('viewport', 30)}   pixel ratio: {short('pixel_ratio', 10)}",
        (f"secure page (microphone allowed): {short('secure', 10)}   speech recognition: {short('speech', 10)}   "
        f"page address scheme: {short('scheme_url', 10)}   port: {short('port', 10)}"),
    ]
    problems = client.get("problems")
    if isinstance(problems, list) and problems:
        lines.append("problems seen by this page:")
        lines += [f"  {scrub(str(p))[:300]}" for p in problems[-30:]]
    else:
        lines.append("problems seen by this page: none")
    return lines


# ------------------------------------------------------------------ the whole file ---
def build(cfg: Config, *, runtime_info: dict, state: dict | None, state_problem: str, client: dict,
          photo_folder: Path, own_photos: int, shown_photos: int, now: datetime) -> str:
    from . import tls

    info = system.install_info()
    out = [
        "BERANDA DIAGNOSTIC FILE",
        f"made on {now.astimezone().strftime('%Y-%m-%d %H:%M %Z')} ({now.astimezone(UTC).strftime('%H:%M')} UTC)",
        "Contains no password, calendar link, Dropbox link, feed address or PIN: web addresses are cut to",
        "their site name and the place is rounded to about 10 km. Read it before you share it.",
        "",
        "== BERANDA ==",
        (f"version: {__version__}   commit: {info.get('COMMIT', '-')}   branch: {info.get('BRANCH', '-')}   "
        f"installed with install.sh: {bool(info)}"),
        f"running for: {int(time.time() - START) // 60} min   demo mode: {cfg.demo}",
        (f"listening on: port {runtime_info.get('port')} (saved: {cfg.port})   "
        f"https on the same port: {'yes' if tls.available() else 'no'}"),
        f"settings file: {'found' if runtime_info.get('config_exists') else 'not written yet'}",
        "",
        "== DEVICE ==",
        *device_lines(),
        "",
        "== SETTINGS ==",
        *settings_lines(cfg, photo_folder, own_photos, shown_photos),
        "",
        "== WHAT THE DISPLAY SHOWS NOW ==",
        *state_lines(state, state_problem),
        "",
        "== WHAT THE SCREENS REPORTED (microphone, page errors; newest last) ==",
        *display_lines(),
        "",
        "== THE BROWSER OF THE SETTINGS PAGE ==",
        *client_lines(client),
        "",
        "== RECENT LOG LINES (Beranda only, newest last) ==",
    ]
    lines = list(_buffer.lines)[-120:] if _buffer else []
    out += lines or ["(nothing logged yet)"]
    return "\n".join(out) + "\n"
