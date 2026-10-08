"""The Beranda web app: one JSON endpoint for the data, static files for the display."""

from __future__ import annotations

import asyncio
import calendar as _calendar
import hashlib
import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .admin import Runtime
from .admin import router as admin_router
from .cache import Cache
from .config import Config
from .providers import astro as astro_mod
from .providers import calendar_ics, demo, news_catalog, seasons, specialdays
from .providers import news as news_mod
from .providers import weather as weather_mod

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent / "web"
THEMES = set(seasons.THEMES)
WEATHER_TTL = 15 * 60
CALENDAR_TTL = 15 * 60
NEWS_TTL = 30 * 60

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
    cfg: Config, cache: Cache, now: datetime, theme: str | None = None
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
        "season": seasons.current(theme or cfg.theme, today, loc.timezone, loc.latitude),
        "events": events,
        "special_days": days,
        "news": news,
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

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/api/state")
    async def state(theme: str | None = None) -> JSONResponse:
        # `theme` lets the admin preview another theme with its own seasonal calendar.
        theme = theme if theme in THEMES else None
        data = await build_state(runtime.cfg, cache, clock(), theme)
        return JSONResponse(data, headers={"Cache-Control": "no-store"})

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/admin")
    async def admin_page() -> FileResponse:
        return FileResponse(WEB_DIR / "admin.html", headers={"Cache-Control": "no-cache"})

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
    return app
