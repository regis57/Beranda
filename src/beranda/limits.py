"""How much Beranda lets you add, adapted to the computer it runs on.

Every calendar, news feed or TV channel you add is one more thing to download and keep in
memory, and a small Raspberry Pi has little of either. Beranda reads the model of the board
and its memory, picks one of five profiles, and uses it for the maximum number of calendars,
news sources, TV channels, radio stations, dates, photos and voice phrases.

Your own choice always wins: `[limits] profile = "plus"` in config.toml (or the environment
variable BERANDA_PROFILE) forces a profile, for example if you know your Pi copes with more.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

PROFILES = ("lite", "standard", "comfort", "plus", "max")


@dataclass(frozen=True)
class Limits:
    profile: str
    calendars: int  # calendar links (.ics)
    news_sources: int  # news media + your own feeds, together
    tv_channels: int  # TV channels ticked
    radio_stations: int  # favourite radio stations
    key_dates: int  # your own dates (birthdays...)
    photos: int  # pictures kept in the photo frame
    voice_commands: int  # your own voice phrases


# One row per profile, in the order of PROFILES.
_TABLE = {
    #            calendars, news, tv, radio, dates, photos, voice
    "lite":     (3, 8, 15, 15, 100, 200, 20),
    "standard": (10, 20, 40, 30, 200, 500, 50),
    "comfort":  (15, 30, 60, 50, 400, 800, 80),
    "plus":     (25, 50, 100, 80, 800, 1500, 120),
    "max":      (40, 80, 150, 120, 1500, 3000, 200),
}


def for_profile(name: str) -> Limits:
    row = _TABLE[name if name in _TABLE else "standard"]
    return Limits(name if name in _TABLE else "standard", *row)


def _read(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace").replace("\x00", "").strip()
    except OSError:
        return ""


def memory_gb() -> int:
    """The board's memory as the number printed on the box: 1, 2, 4, 8 or 16 (the system shows
    a little less than that, hence the loose thresholds)."""
    match = re.search(r"MemTotal:\s+(\d+)", _read("/proc/meminfo"))
    gib = int(match.group(1)) / 1024 / 1024 if match else 1.0
    for box, ceiling in ((1, 1.3), (2, 2.6), (4, 5.5), (8, 11.0)):
        if gib < ceiling:
            return box
    return 16


_BY_MEMORY = {1: "standard", 2: "comfort", 4: "plus", 8: "max", 16: "max"}


def classify(model: str, ram_gb: int) -> str:
    """Pick a profile from the board's name and memory (a pure function, easy to test)."""
    low = model.lower()
    if "raspberry pi" in low:
        if "zero" in low or re.search(r"raspberry pi (model|1|2)\b", low) or "pi 2" in low:
            return "lite"  # Pi 1, Pi 2, Zero, Zero 2: slow CPU and 512 MB - 1 GB
        if re.search(r"raspberry pi (3|compute module 3)", low):
            return "standard"
        # Pi 4, 400, 5, 500 and their compute modules: the memory tells the story
    return _BY_MEMORY.get(ram_gb, "standard")


def device() -> tuple[str, int]:
    """(board name, memory in GB): ("Raspberry Pi 4 Model B Rev 1.4", 4), or ("", 8) elsewhere."""
    return _read("/proc/device-tree/model"), memory_gb()


def resolve(configured: str = "auto") -> Limits:
    """The profile in use: config.toml, then BERANDA_PROFILE, then what the machine looks like."""
    for choice in (configured, os.environ.get("BERANDA_PROFILE", "")):
        if choice in PROFILES:
            return for_profile(choice)
    model, ram = device()
    return for_profile(classify(model, ram))


def too_many(body: dict, limits: Limits) -> str | None:
    """A plain sentence naming the first list that is over its limit in a settings body, or None."""
    news = body.get("news") or {}
    own_feeds = len(news.get("feeds") or [])
    chosen = news.get("sources")
    checks = (
        ("calendars", len((body.get("calendar") or {}).get("ics_urls") or []), limits.calendars),
        ("key dates", len(body.get("key_dates") or []), limits.key_dates),
        ("news sources", own_feeds + (len(chosen) if chosen is not None else 0), limits.news_sources),
        ("TV channels", len((body.get("tv") or {}).get("channels") or []), limits.tv_channels),
        ("radio stations", len((body.get("radio") or {}).get("stations") or []), limits.radio_stations),
        ("voice phrases", len((body.get("voice") or {}).get("commands") or []), limits.voice_commands),
    )
    for name, count, maximum in checks:
        if count > maximum:
            return f"too many {name}: {count} (this device allows {maximum})"
    return None
