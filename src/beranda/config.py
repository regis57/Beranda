"""Configuration loading. One small TOML file, sensible defaults, no surprises."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .providers import voice as voice_mod

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
class Station:
    """A radio station the user picked as a favourite, kept as given by Radio Browser."""

    uuid: str
    name: str
    url: str
    favicon: str = ""
    country: str = ""


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
    admin_pin: str = ""  # optional PIN for the admin page; empty = open to the home network
    news_enabled: bool = True
    news_sources: tuple[str, ...] | None = None  # None = let Beranda choose (town, country, world)
    news_feeds: tuple[str, ...] = ()  # the user's own RSS/Atom links
    screen_rotate: int = 0  # 0, 90, 180 or 270 degrees (applied by the kiosk on the Pi)
    screen_off: str = ""  # "23:00": turn the screen off at night ("" = never)
    screen_on: str = ""  # "06:30": and back on in the morning
    photos_folder: str = ""  # local folder of pictures ("" = carousel disabled); fill it with
    # rclone or Syncthing so photos from a phone or a cloud account land here on their own
    photos_interval: int = 20  # seconds a photo stays full-screen before the dashboard returns
    radio_stations: tuple[Station, ...] = ()  # favourites, picked on the settings page
    radio_volume: int = 70  # 0-100
    tv_xmltv_url: str = ""  # the user's own XMLTV guide address ("" = TV section disabled)
    tv_channels: tuple[str, ...] = ()  # channel ids (from that guide) to show prime time for
    tv_prime_start: str = "20:00"  # "HH:MM", local time
    tv_prime_end: str = "23:00"  # if this is not after the start, it is treated as past midnight
    voice_enabled: bool = False  # the beranda-voice service only acts when this is on
    voice_wake_word: str = voice_mod.DEFAULT_WAKE_WORD  # one of the pretrained wake phrases
    history_enabled: bool = True  # "on this day" historical events for `country`, from Wikidata

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


def _parse_station(raw: dict) -> Station:
    url = str(raw.get("url", "")).strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"a radio station needs a stream url, got {url[:60]!r}")
    return Station(
        uuid=str(raw.get("uuid", "")),
        name=str(raw.get("name", "")).strip() or "?",
        url=url,
        favicon=str(raw.get("favicon", "")),
        country=str(raw.get("country", "")),
    )


def normalise_language(raw: object) -> str:
    """'PT_br' -> 'pt-BR', 'FR' -> 'fr'. Anything odd falls back to English."""
    text = str(raw or "en").strip().replace("_", "-")
    base, _, region = text.partition("-")
    base = base.lower()
    if not base.isalpha() or not 2 <= len(base) <= 3:
        return "en"
    if region and region.isalpha() and len(region) == 2:
        return f"{base}-{region.upper()}"
    return base


def _check_feed(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"a news feed must start with http:// or https://, got {url[:60]!r}")
    return url


def _check_interval(value: object, minimum: int, default: int) -> int:
    seconds = int(value if value is not None else default)
    if seconds < minimum:
        raise ValueError(f"interval must be at least {minimum} seconds, got {seconds}")
    return seconds


def _check_tv_url(value: object) -> str:
    url = str(value or "").strip()
    if url and not url.lower().startswith(("http://", "https://")):
        raise ValueError(f"the TV guide address must start with http:// or https://, got {url[:60]!r}")
    return url


def _check_rotate(value: object) -> int:
    rotate = int(value or 0)
    if rotate not in {0, 90, 180, 270}:
        raise ValueError("screen rotation must be 0, 90, 180 or 270")
    return rotate


def _check_hhmm(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    hours, _, minutes = text.partition(":")
    if not (hours.isdigit() and minutes.isdigit() and int(hours) < 24 and int(minutes) < 60):
        raise ValueError(f"times are written HH:MM, like 23:00, got {text!r}")
    return f"{int(hours):02d}:{int(minutes):02d}"


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
    news = data.get("news", {})
    screen = data.get("screen", {})
    photos = data.get("photos", {})
    radio = data.get("radio", {})
    tv = data.get("tv", {})
    voice = data.get("voice", {})
    history = data.get("history", {})
    cache_dir = Path(data.get("cache_dir", Config.cache_dir)).expanduser()

    return Config(
        location=location,
        country=country,
        subdivision=data.get("subdivision"),
        language=normalise_language(data.get("language", "fr")),
        units=units,
        theme=data.get("theme", "japan"),
        mode=mode,
        ics_urls=tuple(data.get("calendar", {}).get("ics_urls", [])),
        key_dates=tuple(_parse_key_date(k) for k in data.get("key_dates", [])),
        demo=bool(data.get("demo", False)),
        host=server.get("host", "0.0.0.0"),
        port=int(server.get("port", 8080)),
        cache_dir=cache_dir,
        admin_pin=str(data.get("admin", {}).get("pin", "")),
        news_enabled=bool(news.get("enabled", True)),
        news_sources=None if news.get("sources") is None else tuple(str(x) for x in news["sources"]),
        news_feeds=tuple(_check_feed(str(u)) for u in news.get("feeds", [])),
        screen_rotate=_check_rotate(screen.get("rotate", 0)),
        screen_off=_check_hhmm(screen.get("off", "")),
        screen_on=_check_hhmm(screen.get("on", "")),
        photos_folder=str(photos.get("folder", "")).strip(),
        photos_interval=_check_interval(photos.get("interval"), 5, Config.photos_interval),
        radio_stations=tuple(_parse_station(s) for s in radio.get("stations", [])),
        radio_volume=max(0, min(100, int(radio.get("volume", Config.radio_volume)))),
        tv_xmltv_url=_check_tv_url(tv.get("url", "")),
        tv_channels=tuple(str(c) for c in tv.get("channels", [])),
        tv_prime_start=_check_hhmm(tv.get("prime_start")) or Config.tv_prime_start,
        tv_prime_end=_check_hhmm(tv.get("prime_end")) or Config.tv_prime_end,
        voice_enabled=bool(voice.get("enabled", False)),
        voice_wake_word=voice_mod.check_wake_word(voice.get("wake_word")),
        history_enabled=bool(history.get("enabled", True)),
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
    if path is None or not Path(path).is_file():
        return Config()  # first start: nothing saved yet (BERANDA_CONFIG may name a future file)
    with open(path, "rb") as fh:
        return from_dict(tomllib.load(fh))


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "beranda" / "config.toml"


def to_dict(cfg: Config) -> dict:
    """The inverse of from_dict: what we write back to config.toml."""
    keys = []
    for k in cfg.key_dates:
        date_text = f"{k.year:04d}-{k.month:02d}-{k.day:02d}" if k.year else f"{k.month:02d}-{k.day:02d}"
        keys.append({"date": date_text, "label": k.label, "kind": k.kind})
    out: dict = {
        "country": cfg.country,
        "language": cfg.language,
        "units": cfg.units,
        "theme": cfg.theme,
        "mode": cfg.mode,
        "location": {
            "name": cfg.location.name,
            "latitude": cfg.location.latitude,
            "longitude": cfg.location.longitude,
            "timezone": cfg.location.timezone,
        },
        "calendar": {"ics_urls": list(cfg.ics_urls)},
        "key_dates": keys,
        "server": {"host": cfg.host, "port": cfg.port},
    }
    news: dict = {"enabled": cfg.news_enabled, "feeds": list(cfg.news_feeds)}
    if cfg.news_sources is not None:
        news["sources"] = list(cfg.news_sources)
    out["news"] = news
    out["screen"] = {"rotate": cfg.screen_rotate, "off": cfg.screen_off, "on": cfg.screen_on}
    out["photos"] = {"folder": cfg.photos_folder, "interval": cfg.photos_interval}
    out["radio"] = {
        "stations": [
            {"uuid": s.uuid, "name": s.name, "url": s.url, "favicon": s.favicon, "country": s.country}
            for s in cfg.radio_stations
        ],
        "volume": cfg.radio_volume,
    }
    out["tv"] = {
        "url": cfg.tv_xmltv_url,
        "channels": list(cfg.tv_channels),
        "prime_start": cfg.tv_prime_start,
        "prime_end": cfg.tv_prime_end,
    }
    out["voice"] = {"enabled": cfg.voice_enabled, "wake_word": cfg.voice_wake_word}
    out["history"] = {"enabled": cfg.history_enabled}
    if cfg.subdivision:
        out["subdivision"] = cfg.subdivision
    if cfg.admin_pin:
        out["admin"] = {"pin": cfg.admin_pin}
    return out
