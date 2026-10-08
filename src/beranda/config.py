"""Configuration loading. One small TOML file, sensible defaults, no surprises."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Countries whose weeks conventionally start on Sunday (the rest start on Monday).
SUNDAY_FIRST = {
    "US", "CA", "MX", "JP", "BR", "AU", "IL", "IN", "KR", "TW", "PH", "ZA", "SA", "CO", "PE",
    "VE", "HK", "ID", "TH", "AR", "CL",
}
IMPERIAL_COUNTRIES = {"US", "LR", "MM"}

CONFIG_SEARCH_PATHS = (
    Path("beranda.toml"),
    Path.home() / ".config" / "beranda" / "config.toml",
    Path("/etc/beranda/config.toml"),
)


@dataclass(frozen=True)
class Location:
    name: str = "Metz"
    latitude: float = 49.1193
    longitude: float = 6.1757
    timezone: str = "Europe/Paris"


@dataclass(frozen=True)
class KeyDate:
    """A personal date shown on the calendar: birth, death, anniversary, other."""

    month: int
    day: int
    label: str
    kind: str = "other"  # birth | death | anniversary | other
    year: int | None = None  # when known, lets us show an age / number of years


@dataclass(frozen=True)
class Config:
    location: Location = field(default_factory=Location)
    country: str = "FR"  # ISO 3166-1 alpha-2
    subdivision: str | None = None  # region for regional public holidays
    language: str = "fr"
    units: str = "metric"  # metric | imperial
    theme: str = "japan"
    mode: str = "auto"  # auto | light | night
    ics_urls: tuple[str, ...] = ()
    key_dates: tuple[KeyDate, ...] = ()
    demo: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    cache_dir: Path = Path.home() / ".cache" / "beranda"

    @property
    def week_start(self) -> int:
        """0 = Monday, 6 = Sunday."""
        return 6 if self.country.upper() in SUNDAY_FIRST else 0


def _parse_key_date(raw: dict) -> KeyDate:
    """Accept "MM-DD" or "YYYY-MM-DD" in the `date` field."""
    parts = str(raw["date"]).split("-")
    if len(parts) == 3:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    elif len(parts) == 2:
        year, month, day = None, int(parts[0]), int(parts[1])
    else:
        raise ValueError(f"key date must be MM-DD or YYYY-MM-DD, got {raw['date']!r}")
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise ValueError(f"key date out of range: {raw['date']!r}")
    kind = raw.get("kind", "other")
    if kind not in {"birth", "death", "anniversary", "other"}:
        raise ValueError(f"unknown key date kind: {kind!r}")
    return KeyDate(month=month, day=day, label=str(raw["label"]), kind=kind, year=year)


def from_dict(data: dict) -> Config:
    """Build a Config from a parsed TOML dict, validating what matters."""
    loc = data.get("location", {})
    location = Location(
        name=loc.get("name", Location.name),
        latitude=float(loc.get("latitude", Location.latitude)),
        longitude=float(loc.get("longitude", Location.longitude)),
        timezone=loc.get("timezone", Location.timezone),
    )
    if not (-90 <= location.latitude <= 90 and -180 <= location.longitude <= 180):
        raise ValueError("location latitude/longitude out of range")

    country = str(data.get("country", "FR")).upper()
    units = data.get("units") or ("imperial" if country in IMPERIAL_COUNTRIES else "metric")
    if units not in {"metric", "imperial"}:
        raise ValueError("units must be 'metric' or 'imperial'")
    mode = data.get("mode", "auto")
    if mode not in {"auto", "light", "night"}:
        raise ValueError("mode must be 'auto', 'light' or 'night'")

    server = data.get("server", {})
    cache_dir = Path(data.get("cache_dir", Config.cache_dir)).expanduser()

    return Config(
        location=location,
        country=country,
        subdivision=data.get("subdivision"),
        language=str(data.get("language", "fr")).lower(),
        units=units,
        theme=data.get("theme", "japan"),
        mode=mode,
        ics_urls=tuple(data.get("calendar", {}).get("ics_urls", [])),
        key_dates=tuple(_parse_key_date(k) for k in data.get("key_dates", [])),
        demo=bool(data.get("demo", False)),
        host=server.get("host", "0.0.0.0"),
        port=int(server.get("port", 8080)),
        cache_dir=cache_dir,
    )


def find_config_path() -> Path | None:
    env = os.environ.get("BERANDA_CONFIG")
    if env:
        return Path(env)
    for candidate in CONFIG_SEARCH_PATHS:
        if candidate.is_file():
            return candidate
    return None


def load(path: Path | None = None) -> Config:
    """Load the config file if there is one, defaults otherwise."""
    path = path or find_config_path()
    if path is None:
        return Config()
    with open(path, "rb") as fh:
        return from_dict(tomllib.load(fh))
