"""The admin page's API: read and write the config file from a phone or laptop.

Safety, because this endpoint can change what the mirror does and holds secret calendar links:
  * only addresses from a private network (or this machine) are accepted;
  * an optional PIN, sent in the X-Beranda-Pin header;
  * writes must come from the same origin (no cross-site form posts);
  * the config file is written atomically and readable only by its owner.
"""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import logging
import os
import tempfile
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import tomli_w
from fastapi import APIRouter, Depends, HTTPException, Request

from . import __version__, system
from . import config as config_mod
from . import limits as limits_mod
from .config import Config
from .providers import alerts, calendar_ics, news_catalog, photos, radio, seasons, tv, tv_guides
from .providers import countries as world
from .providers import news as news_mod
from .providers import voice as voice_mod

log = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "Beranda/0.4 (+https://github.com/regis57/Beranda)"
# Languages the display is translated into (the settings page falls back to English).
LANGUAGES = world.LANGUAGES


DROPBOX_EVERY_SECONDS = 6 * 60 * 60  # how often a Dropbox folder is copied again


@dataclass
class Runtime:
    """What the running app reads on every request; the admin page can replace `cfg`."""

    cfg: Config
    config_path: Path | None  # None: nowhere to save (demo mode)
    dropbox: dict = field(default_factory=dict)  # result of the last Dropbox copy, for the page
    _tasks: set = field(default_factory=set)
    listening_port: int = field(init=False, default=0)  # the port this server really listens on

    def __post_init__(self) -> None:
        self.listening_port = self.cfg.port  # a new port saved later only applies after a restart

    @property
    def photo_folder(self) -> Path:
        return photos.effective_folder(self.cfg.photos_folder)

    async def sync_dropbox(self) -> dict:
        """Copy the shared Dropbox folder into the photo folder and remember how it went."""
        when = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            result = await photos.sync_dropbox(self.cfg.photos_dropbox_url, self.photo_folder, self.cfg.limits.photos)
            self.dropbox = {"ok": True, "at": when, **result}
        except photos.PhotoError as exc:  # bad link, too big, not a folder: the page words it
            self.dropbox = {"ok": False, "at": when, "error": str(exc), "code": exc.code}
        except (httpx.HTTPError, OSError) as exc:
            self.dropbox = {"ok": False, "at": when, "error": type(exc).__name__, "code": "net"}
        return self.dropbox

    def sync_dropbox_soon(self) -> None:
        """Start a copy in the background (the settings page must not wait for a download)."""
        task = asyncio.create_task(self.sync_dropbox())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def dropbox_loop(self) -> None:
        """Runs for the life of the server: copy the Dropbox folder now, then every few hours."""
        await asyncio.sleep(30)  # let the screen come up first
        while True:
            try:
                if self.cfg.photos_dropbox_url and not self.cfg.demo:
                    await self.sync_dropbox()
            except Exception:
                log.exception("Dropbox copy failed")
            await asyncio.sleep(DROPBOX_EVERY_SECONDS)


def _is_local(host: str | None) -> bool:
    try:
        ip = ipaddress.ip_address(host or "")
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_private or ip.is_loopback or ip.is_link_local


def write_config(path: Path, cfg: Config) -> None:
    """Atomic write, 0600: the file can contain secret calendar addresses."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            tomli_w.dump(config_mod.to_dict(cfg), fh)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def router(runtime: Runtime) -> APIRouter:
    api = APIRouter(prefix="/api/admin")

    async def guard(request: Request) -> None:
        if not _is_local(request.client.host if request.client else None):
            raise HTTPException(403, "admin is only available from your home network")
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            if origin and urlparse(origin).netloc != request.headers.get("host"):
                raise HTTPException(403, "cross-origin request refused")
        pin = runtime.cfg.admin_pin
        if pin and not hmac.compare_digest(request.headers.get("x-beranda-pin", ""), pin):
            raise HTTPException(401, "PIN required")

    @api.get("/status")
    async def status(request: Request) -> dict:
        """Open to the local network without a PIN: tells the page whether to ask for one."""
        if not _is_local(request.client.host if request.client else None):
            raise HTTPException(403, "admin is only available from your home network")
        return {"pin_required": bool(runtime.cfg.admin_pin)}

    @api.get("/config", dependencies=[Depends(guard)])
    async def get_config() -> dict:
        import holidays

        data = config_mod.to_dict(runtime.cfg)
        data.pop("admin", None)
        data.pop("server", None)
        # The library lists every country twice (FR and FRA) plus aliases (UK): keep ISO alpha-2.
        countries = {
            code: sorted(subs)
            for code, subs in holidays.list_supported_countries().items()
            if len(code) == 2 and code != "UK"
        }
        cfg = runtime.cfg
        return {
            "config": data,
            "pin_set": bool(cfg.admin_pin),
            "limits": {**vars(cfg.limits), "device": limits_mod.device()[0], "memory_gb": limits_mod.device()[1]},
            "editable": runtime.config_path is not None,
            # first visit: no config file yet, the page shows a short welcome
            "first_run": runtime.config_path is not None and not runtime.config_path.exists(),
            "news_auto": news_catalog.automatic(cfg.country, cfg.language, cfg.location.name),
            "photos_info": {
                "folder": str(runtime.photo_folder),
                "custom": bool(cfg.photos_folder.strip()),
                "dropbox": runtime.dropbox,
            },
            "options": {
                "countries": countries,
                "languages": list(LANGUAGES),
                "themes": list(seasons.THEMES),
                "news": [
                    {k: v for k, v in src.items() if k != "url"} for src in news_catalog.SOURCES
                ],
                "region_of": world.REGION_OF,
                "country_languages": world.COUNTRY_LANGUAGES,
            },
        }

    @api.put("/config", dependencies=[Depends(guard)])
    async def put_config(body: dict) -> dict:
        if runtime.config_path is None:
            raise HTTPException(409, "nowhere to save the settings")
        over = limits_mod.too_many(body, runtime.cfg.limits)
        if over:
            raise HTTPException(422, f"invalid settings: {over}")
        merged = dict(body)
        merged["server"] = {"host": runtime.cfg.host, "port": runtime.cfg.port}
        if "pin" in merged:  # "" clears, a string sets, absent keeps
            merged["admin"] = {"pin": str(merged.pop("pin"))}
        elif runtime.cfg.admin_pin:
            merged["admin"] = {"pin": runtime.cfg.admin_pin}
        sources = (merged.get("news") or {}).get("sources")
        if sources is not None:
            unknown = [x for x in sources if x != "city" and x not in news_catalog.BY_ID]
            if unknown:
                raise HTTPException(422, f"invalid settings: unknown news source {unknown[0]!r}")
        try:
            new = config_mod.from_dict(merged)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, f"invalid settings: {exc}") from exc
        new = replace(new, demo=runtime.cfg.demo, cache_dir=runtime.cfg.cache_dir)
        write_config(runtime.config_path, new)
        new_link = new.photos_dropbox_url and new.photos_dropbox_url != runtime.cfg.photos_dropbox_url
        runtime.cfg = new
        if new_link and not new.demo:
            runtime.sync_dropbox_soon()
        return {"saved": True, "path": str(runtime.config_path)}

    @api.get("/geocode", dependencies=[Depends(guard)])
    async def geocode(q: str, language: str = "en") -> dict:
        if len(q.strip()) < 2:
            return {"results": []}
        try:
            async with httpx.AsyncClient(timeout=8, headers={"User-Agent": USER_AGENT}) as client:
                r = await client.get(
                    GEOCODE_URL, params={"name": q.strip(), "count": 6, "language": language[:2]}
                )
                r.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"search unavailable ({type(exc).__name__})") from exc
        found = [
            {
                "name": item.get("name"),
                "region": item.get("admin1"),
                "area": item.get("admin2") or item.get("admin1") or "",  # often the department / county
                "country": item.get("country_code"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "timezone": item.get("timezone"),
            }
            for item in r.json().get("results", [])
        ]
        return {"results": found}

    @api.post("/test-ics", dependencies=[Depends(guard)])
    async def test_ics(body: dict) -> dict:
        from datetime import timedelta
        from zoneinfo import ZoneInfo

        url = str(body.get("url", ""))
        tz = runtime.cfg.location.timezone
        try:
            text = await calendar_ics.download(url)
            today = datetime.now(ZoneInfo(tz)).date()
            events = calendar_ics.events_from_ics(text, today, today + timedelta(days=60), tz)
        except Exception as exc:  # noqa: BLE001 - class name only: the URL is a secret
            return {"ok": False, "error": type(exc).__name__}
        return {
            "ok": True,
            "count": len(events),
            # title + start (ISO), so the page can say "Tuesday 3 Nov - dentist"
            "next": [{"title": e["title"], "start": e["start"], "all_day": e["all_day"]} for e in events[:3]],
        }

    @api.get("/photos", dependencies=[Depends(guard)])
    async def photos_list() -> dict:
        return {
            "folder": str(runtime.photo_folder),
            "names": photos.list_photos(runtime.photo_folder, runtime.cfg.limits.photos),
            "max": runtime.cfg.limits.photos,
            "dropbox": runtime.dropbox,
        }

    @api.post("/photos", dependencies=[Depends(guard)])
    async def photos_add(request: Request, name: str = "photo.jpg") -> dict:
        """Receive one picture as the raw request body (no form encoding: nothing extra to install)."""
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > photos.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "that picture is too big (15 MB at most)")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > photos.MAX_UPLOAD_BYTES:
                raise HTTPException(413, "that picture is too big (15 MB at most)")
            chunks.append(chunk)
        room = runtime.cfg.limits.photos
        if len(photos.list_photos(runtime.photo_folder, room)) >= room:
            raise HTTPException(409, f"the photo frame is full ({room} pictures on this device)")
        try:
            saved = photos.save(runtime.photo_folder, name, b"".join(chunks))
        except photos.PhotoError as exc:
            raise HTTPException(413 if exc.code == "big" else 422, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(500, f"could not save the picture ({type(exc).__name__})") from exc
        return {"saved": saved}

    @api.delete("/photos/{name}", dependencies=[Depends(guard)])
    async def photos_remove(name: str) -> dict:
        if not photos.delete(runtime.photo_folder, name):
            raise HTTPException(404, "no such picture")
        return {"deleted": name}

    @api.post("/photos-sync", dependencies=[Depends(guard)])
    async def photos_sync() -> dict:
        if not runtime.cfg.photos_dropbox_url:
            raise HTTPException(409, "no Dropbox link is saved yet")
        return await runtime.sync_dropbox()

    @api.get("/photos-count", dependencies=[Depends(guard)])
    async def photos_count(folder: str = "") -> dict:
        """Live feedback while the user types a folder path, before they save it."""
        return {"count": len(photos.list_photos(photos.effective_folder(folder), runtime.cfg.limits.photos))}

    @api.get("/radio-search", dependencies=[Depends(guard)])
    async def radio_search(country: str = "", language: str = "", name: str = "") -> dict:
        try:
            stations = await radio.search(country=country, language=language, name=name)
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"radio directory unavailable ({type(exc).__name__})") from exc
        return {"stations": stations}

    @api.get("/tv-guides", dependencies=[Depends(guard)])
    async def tv_guides_for(country: str = "") -> dict:
        """Which guide addresses for this country answer right now (a few seconds' check)."""
        code = (country or runtime.cfg.country).upper()[:2]
        return {"country": code, "guides": await tv_guides.available(code), "project": tv_guides.PROJECT_PAGE}

    @api.post("/test-tv", dependencies=[Depends(guard)])
    async def test_tv(body: dict) -> dict:
        """Download the guide once and list its channels, for the settings page's picker."""
        url = str(body.get("url", "")).strip()
        try:
            raw = await tv.download(url)
            found = tv.channels(raw)
        except Exception as exc:  # noqa: BLE001 - class name only: the URL may be private
            return {"ok": False, "error": type(exc).__name__}
        return {"ok": True, "channels": found}

    @api.post("/test-alerts", dependencies=[Depends(guard)])
    async def test_alerts(body: dict) -> dict:
        """Read the country's warning feed once and say whether the typed area is understood."""
        country = str(body.get("country") or runtime.cfg.country).upper()[:2]
        area = " ".join(str(body.get("area", "")).split())[:80]
        if not alerts.supported(country):
            return {"ok": False, "error": "unsupported"}
        try:
            every = await alerts.fetch(country, datetime.now(UTC))
        except Exception as exc:  # noqa: BLE001 - class name only
            return {"ok": False, "error": type(exc).__name__}
        mine = alerts.for_area(every, area, limit=10)
        return {
            "ok": True,
            "warned_areas": sorted({w["area"] for w in every})[:40],  # the areas with a warning right now
            "mine": [{"kind": w["kind"], "level": w["level"], "event": w["event"]} for w in mine],
        }

    @api.get("/voice-commands", dependencies=[Depends(guard)])
    async def voice_commands(language: str = "") -> dict:
        """The phrases Beranda understands out of the box, in the display language."""
        lang = config_mod.normalise_language(language or runtime.cfg.language)
        return {
            "language": lang,
            "commands": voice_mod.default_commands(lang),
            "actions": list(config_mod.VOICE_ACTIONS),
        }

    @api.get("/system", dependencies=[Depends(guard)])
    async def system_info() -> dict:
        info = system.install_info()
        return {
            "version": __version__,
            "installed": bool(info),
            "commit": info.get("COMMIT", ""),
            "branch": info.get("BRANCH", "main"),
            "screen": info.get("SCREEN", "0") == "1",
            "actions": system.requests_dir() is not None,
            "port": runtime.listening_port,
            "saved_port": runtime.cfg.port,  # differs from "port" until Beranda is restarted
        }

    @api.get("/system/latest", dependencies=[Depends(guard)])
    async def system_latest() -> dict:
        latest = await system.latest_version(system.install_info().get("BRANCH", "main"))
        newer = bool(latest) and system.version_tuple(latest) > system.version_tuple(__version__)
        return {"latest": latest, "update_available": newer}

    @api.post("/system/port", dependencies=[Depends(guard)])
    async def change_port(body: dict) -> dict:
        """Move Beranda to another port (the number after the colon in its address).

        The new number is saved in the settings file, the server then stops so that systemd
        starts it again on the new port, and the screen on the Pi is restarted so it opens the
        new address. The page that asked must go to the new address itself."""
        if runtime.config_path is None:
            raise HTTPException(409, "nowhere to save the settings")
        if body.get("confirmed") is not True:
            raise HTTPException(400, "the change must be confirmed")
        port = body.get("port")
        problem = system.port_problem(port, runtime.cfg.port, runtime.cfg.host)
        if problem:
            raise HTTPException(422, f"port_{problem}")
        runtime.cfg = replace(runtime.cfg, port=port)
        write_config(runtime.config_path, runtime.cfg)
        restarting = system.restart_server_soon()
        screen = False
        if restarting and system.install_info().get("SCREEN", "0") == "1":
            try:
                system.request_action("restart-screen")  # the screen reads the port when it starts
                screen = True
            except (RuntimeError, OSError):
                pass
        return {"port": port, "restarting": restarting, "screen": screen}

    @api.post("/system/{action}", dependencies=[Depends(guard)])
    async def system_action(action: str, body: dict | None = None) -> dict:
        # Wiping every setting must be asked for on purpose: the settings page only sends
        # "confirmed" after the person typed the word "yes" (in their language) themselves.
        if action == "reset" and (body or {}).get("confirmed") is not True:
            raise HTTPException(400, "the reset must be confirmed")
        try:
            system.request_action(action)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"requested": action}

    @api.get("/news-auto", dependencies=[Depends(guard)])
    async def news_auto(country: str, language: str, city: str = "") -> dict:
        """What 'choose for me' would pick for these settings (the page shows it live)."""
        lang = config_mod.normalise_language(language)
        return {"sources": news_catalog.automatic(country.upper()[:2], lang, city.strip() or None)}

    @api.post("/test-feed", dependencies=[Depends(guard)])
    async def test_feed(body: dict) -> dict:
        """Read one feed now: a catalog id, 'city' (with the town and language) or a URL."""
        source_id = str(body.get("id", ""))
        if source_id == "city":
            url = news_catalog.city_feed_url(str(body.get("city", "")), str(body.get("language", "en")))
            name = ""
        elif source_id in news_catalog.BY_ID:
            url, name = news_catalog.BY_ID[source_id]["url"], news_catalog.BY_ID[source_id]["name"]
        else:
            url, name = str(body.get("url", "")).strip(), ""
            if not url.lower().startswith(("http://", "https://")):
                return {"ok": False, "error": "NotALink"}
        try:
            items = news_mod.parse(await news_mod.fetch(url), name)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": type(exc).__name__}
        return {"ok": True, "count": len(items), "first": items[0]["title"] if items else ""}

    return api
