"""The Beranda web app: one JSON endpoint for the data, static files for the display."""

from __future__ import annotations

import asyncio
import calendar as _calendar
import hashlib
import io
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, system
from .admin import Runtime
from .admin import router as admin_router
from .cache import Cache
from .config import Config
from .providers import astro as astro_mod
from .providers import calendar_ics, demo, news_catalog, photos, seasons, specialdays
from .providers import history as history_mod
from .providers import news as news_mod
from .providers import tv as tv_mod
from .providers import weather as weather_mod

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"
THEMES = set(seasons.THEMES)
WEATHER_TTL = 15 * 60
CALENDAR_TTL = 15 * 60
NEWS_TTL = 30 * 60
TV_TTL = 3 * 60 * 60  # XMLTV guides are usually refreshed by their publisher a few times a day
HISTORY_TTL = 20 * 60 * 60  # "on this day" only changes once a day, by definition

# The display loads nothing but its own files. A strict policy keeps a hostile calendar
# entry or feed from ever running code on the mirror.
CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'"
)


def _iso_offset(now: datetime) -> str:
    raw = now.strftime("%z")  # +0200
    return f"{raw[:3]}:{raw[3:]}" if raw else "+00:00"


def _window(today: date) -> tuple[date, date]:
    """From the first of this month to the last day of next month."""
    first = today.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    last = nxt.replace(day=_calendar.monthrange(nxt.year, nxt.month)[1])
    return first, last


def _prime_window(now: datetime, start_hhmm: str, end_hhmm: str) -> tuple[datetime, datetime]:
    """Today's prime-time window, in `now`'s own timezone. An end not after the start means
    it runs past midnight (e.g. 20:00 -> 00:30), so we push it a day later."""
    start_h, start_m = (int(x) for x in start_hhmm.split(":"))
    end_h, end_m = (int(x) for x in end_hhmm.split(":"))
    start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def news_plan(cfg: Config) -> list[tuple[str, str, str]]:
    """(key, display name, url) for every feed to read."""
    chosen = cfg.news_sources
    if chosen is None:
        chosen = tuple(news_catalog.automatic(cfg.country, cfg.language, cfg.location.name))
    plan = []
    for source_id in chosen:
        if source_id == "city":
            if cfg.location.name:
                url = news_catalog.city_feed_url(cfg.location.name, cfg.language)
                plan.append(("city", "", url))  # "": the medium is each article's own site
        elif source_id in news_catalog.BY_ID:
            src = news_catalog.BY_ID[source_id]
            plan.append((source_id, src["name"], src["url"]))
    for index, url in enumerate(cfg.news_feeds):
        plan.append((f"feed:{index}", "", url))
    return plan


async def build_news(cfg: Config, cache: Cache, now: datetime, errors: dict, stale: list) -> dict:
    plan = news_plan(cfg)

    async def one(key: str, name: str, url: str) -> list[dict]:
        async def load() -> list[dict]:
            items = news_mod.parse(await news_mod.fetch(url), name)
            for item in items:
                if not item["source"]:
                    item["source"] = item["host"].removeprefix("www.")
            return items

        digest = hashlib.sha1(url.encode()).hexdigest()[:12]
        try:
            items, is_stale = await cache.get(f"news:{digest}", NEWS_TTL, load)
            if is_stale:
                stale.append(f"news:{key}")
            return items
        except Exception as exc:  # noqa: BLE001 - a dead feed must not blank the screen
            errors[f"news:{key}"] = type(exc).__name__
            return []

    results = await asyncio.gather(*(one(*p) for p in plan))
    return {"items": news_mod.merge(list(results), now), "sources": len(plan)}


async def build_state(
    cfg: Config, cache: Cache, now: datetime, theme: str | None = None, setup: dict | None = None
) -> dict:
    loc = cfg.location
    today = now.date()
    start, end = _window(today)
    errors: dict[str, str] = {}
    stale: list[str] = []

    # --- weather -----------------------------------------------------------------
    weather = None
    if cfg.demo:
        weather = demo.weather(today, now, cfg.units)
    else:
        try:
            weather, is_stale = await cache.get(
                f"weather:{loc.latitude:.3f}:{loc.longitude:.3f}:{cfg.units}",
                WEATHER_TTL,
                lambda: weather_mod.fetch(loc.latitude, loc.longitude, cfg.units),
            )
            if is_stale:
                stale.append("weather")
        except Exception as exc:  # noqa: BLE001 - one broken source must not blank the screen
            errors["weather"] = type(exc).__name__

    # --- agenda ------------------------------------------------------------------
    events: list[dict] = []
    if cfg.demo:
        events = demo.events(today, _iso_offset(now), cfg.language)
    for index, url in enumerate(cfg.ics_urls):
        digest = hashlib.sha1(url.encode()).hexdigest()[:12]

        async def load(url=url, index=index) -> list[dict]:
            text = await calendar_ics.download(url)
            return calendar_ics.events_from_ics(text, start, end, loc.timezone, index)

        try:
            got, is_stale = await cache.get(f"ics:{digest}:{start}:{end}", CALENDAR_TTL, load)
            events.extend(got)
            if is_stale:
                stale.append(f"calendar:{index}")
        except Exception as exc:  # noqa: BLE001
            # Class name only: the exception text would contain the secret calendar URL.
            errors[f"calendar:{index}"] = type(exc).__name__
    events.sort(key=lambda e: (e["start"], e["title"]))

    # --- news --------------------------------------------------------------------
    news = None
    if cfg.news_enabled:
        if cfg.demo:
            news = demo.news(cfg.language, now)
        else:
            news = await build_news(cfg, cache, now, errors, stale)

    # --- special days ------------------------------------------------------------
    day_cfg = replace(cfg, key_dates=cfg.key_dates + demo.key_dates(today, cfg.language)) if cfg.demo else cfg
    days = specialdays.special_days(day_cfg, start, end)

    # --- "on this day" historical events for the user's own country (Wikidata) ----------
    history: list[dict] = []
    if cfg.history_enabled and not cfg.demo:

        async def load_history() -> list[dict]:
            return await history_mod.fetch(cfg.country, today.month, today.day, cfg.language)

        try:
            history, is_stale = await cache.get(f"history:{cfg.country}:{today.isoformat()}", HISTORY_TTL, load_history)
            if is_stale:
                stale.append("history")
        except Exception as exc:  # noqa: BLE001 - Wikidata being slow or down must not blank the screen
            errors["history"] = type(exc).__name__

    # --- photo carousel (local folder, filled by rclone/Syncthing, nothing fetched here) ---
    photo_names = photos.list_photos(cfg.photos_folder)

    # --- TV prime time (read-only: the user's own XMLTV guide, never scraped by us) -----
    tv = None
    if cfg.tv_xmltv_url and cfg.tv_channels:
        digest = hashlib.sha1(cfg.tv_xmltv_url.encode()).hexdigest()[:12]
        channel_ids = set(cfg.tv_channels)
        prime_start, prime_end = _prime_window(now, cfg.tv_prime_start, cfg.tv_prime_end)

        async def load_tv() -> list[dict]:
            raw = await tv_mod.download(cfg.tv_xmltv_url)
            found = tv_mod.programmes(raw, channel_ids, prime_start, prime_end)
            tz = ZoneInfo(loc.timezone)
            return [
                {
                    "channel": item["channel"],
                    "title": item["title"],
                    "start": item["start"].astimezone(tz).strftime("%H:%M"),
                    "stop": item["stop"].astimezone(tz).strftime("%H:%M"),
                }
                for item in found
            ]

        try:
            got, is_stale = await cache.get(f"tv:{digest}:{today}", TV_TTL, load_tv)
            tv = {"programmes": got}
            if is_stale:
                stale.append("tv")
        except Exception as exc:  # noqa: BLE001 - a dead guide must not blank the screen
            errors["tv"] = type(exc).__name__

    # --- sky & season (all local) --------------------------------------------------
    sky = astro_mod.astro(now, loc.latitude, loc.longitude, loc.timezone)
    mode = cfg.mode if cfg.mode != "auto" else ("night" if sky["night"] else "light")

    return {
        "version": __version__,
        "generated_at": now.isoformat(timespec="seconds"),
        "demo": cfg.demo,
        "mode": mode,
        "config": {
            "language": cfg.language,
            "country": cfg.country,
            "theme": cfg.theme,
            "units": cfg.units,
            "week_start": cfg.week_start,
            "location": {"name": loc.name, "timezone": loc.timezone},
        },
        "weather": weather,
        "sky": sky,
        "season": seasons.current(theme or cfg.theme, today, loc.timezone, loc.latitude, now),
        "events": events,
        "special_days": days,
        "news": news,
        "photos": {"names": photo_names, "interval": cfg.photos_interval},
        "tv": tv,
        "history": history,
        # Screen hours: the page goes dark, and on the Pi the kiosk also turns the HDMI off.
        "sleep": not system.screen_should_be_on(cfg, now),
        # First start: the screen shows where to open the settings, with a QR code.
        "setup": setup or {"needed": False, "urls": [], "wifi": None},
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "stale": stale,
        "errors": errors,
    }


def create_app(
    cfg: Config,
    now_fn: Callable[[], datetime] | None = None,
    config_path: Path | None = None,
) -> FastAPI:
    runtime = Runtime(cfg=cfg, config_path=config_path)
    clock = now_fn or (lambda: datetime.now(ZoneInfo(runtime.cfg.location.timezone)))
    cache = Cache(cfg.cache_dir)
    app = FastAPI(title="Beranda", version=__version__, docs_url=None, redoc_url=None)
    app.include_router(admin_router(runtime))

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def setup_info() -> dict:
        needed = (
            not runtime.cfg.demo
            and runtime.config_path is not None
            and not runtime.config_path.exists()
        )
        wifi = None if runtime.cfg.demo else system.wifi_setup_status()
        # No network at all yet: the LAN address above cannot work, so show the Wi-Fi network
        # to join instead (the beranda-wifi-setup service, if installed, opens it automatically).
        return {"needed": needed or bool(wifi), "urls": system.lan_addresses(runtime.cfg.port), "wifi": wifi}

    @app.get("/api/screen")
    async def screen() -> dict:
        """Read every 30 s by the kiosk script on the Pi."""
        cfg = runtime.cfg
        return {"on": system.screen_should_be_on(cfg, clock()), "rotate": cfg.screen_rotate}

    @app.get("/api/setup-qr.svg")
    async def setup_qr() -> Response:
        import segno

        urls = system.lan_addresses(runtime.cfg.port) or ["http://localhost:8080/admin"]
        qr = segno.make(urls[-1], error="m")  # the numeric address works even without .local
        buffer = io.BytesIO()
        qr.save(buffer, kind="svg", scale=8, border=2, dark="#111111", light="#ffffff", xmldecl=False)
        return Response(buffer.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})

    @app.get("/api/setup-wifi-qr.svg")
    async def setup_wifi_qr() -> Response:
        """A QR code a phone's camera turns straight into "join this Wi-Fi network" - the
        standard WIFI: format every phone already understands, no app needed."""
        import segno

        wifi = system.wifi_setup_status() or {}
        ssid = str(wifi.get("ssid") or "Beranda setup").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
        qr = segno.make(f"WIFI:T:nopass;S:{ssid};;", error="m")
        buffer = io.BytesIO()
        qr.save(buffer, kind="svg", scale=8, border=2, dark="#111111", light="#ffffff", xmldecl=False)
        return Response(buffer.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"})

    @app.get("/api/photos/{name}")
    async def photo(name: str) -> FileResponse:
        path = photos.resolve(runtime.cfg.photos_folder, name)
        if path is None:
            return JSONResponse({"detail": "not found"}, status_code=404)
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/state")
    async def state(theme: str | None = None) -> JSONResponse:
        # `theme` lets the admin preview another theme with its own seasonal calendar.
        theme = theme if theme in THEMES else None
        data = await build_state(runtime.cfg, cache, clock(), theme, setup_info())
        data["radio"] = runtime.radio.status()
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        return FileResponse(WEB_DIR / "admin.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app
