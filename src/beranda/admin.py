"""The admin page's API: read and write the config file from a phone or laptop.

Safety, because this endpoint can change what the mirror does and holds secret calendar links:
  * only addresses from a private network (or this machine) are accepted;
  * an optional PIN, sent in the X-Beranda-Pin header;
  * writes must come from the same origin (no cross-site form posts);
  * the config file is written atomically and readable only by its owner.
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlparse

import httpx
import tomli_w
from fastapi import APIRouter, Depends, HTTPException, Request

from . import config as config_mod
from .config import Config
from .providers import calendar_ics

log = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
USER_AGENT = "Beranda/0.2 (+https://github.com/regis57/Beranda)"
LANGUAGES = ("fr", "en", "ja", "id")  # languages the display is translated into


@dataclass
class Runtime:
    """What the running app reads on every request; the admin page can replace `cfg`."""

    cfg: Config
    config_path: Path | None  # None: nowhere to save (demo mode)


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
        countries = {
            code: sorted(subs) for code, subs in holidays.list_supported_countries().items()
        }
        return {
            "config": data,
            "pin_set": bool(runtime.cfg.admin_pin),
            "editable": runtime.config_path is not None,
            "options": {
                "countries": countries,
                "languages": list(LANGUAGES),
                "themes": ["japan", "indonesia", "france"],
            },
        }

    @api.put("/config", dependencies=[Depends(guard)])
    async def put_config(body: dict) -> dict:
        if runtime.config_path is None:
            raise HTTPException(409, "nowhere to save the settings")
        merged = dict(body)
        merged["server"] = {"host": runtime.cfg.host, "port": runtime.cfg.port}
        if "pin" in merged:  # "" clears, a string sets, absent keeps
            merged["admin"] = {"pin": str(merged.pop("pin"))}
        elif runtime.cfg.admin_pin:
            merged["admin"] = {"pin": runtime.cfg.admin_pin}
        try:
            new = config_mod.from_dict(merged)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, f"invalid settings: {exc}") from exc
        new = replace(new, demo=runtime.cfg.demo, cache_dir=runtime.cfg.cache_dir)
        write_config(runtime.config_path, new)
        runtime.cfg = new
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
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        url = str(body.get("url", ""))
        tz = runtime.cfg.location.timezone
        try:
            text = await calendar_ics.download(url)
            today = datetime.now(ZoneInfo(tz)).date()
            events = calendar_ics.events_from_ics(text, today, today + timedelta(days=60), tz)
        except Exception as exc:  # noqa: BLE001 - class name only: the URL is a secret
            return {"ok": False, "error": type(exc).__name__}
        return {"ok": True, "count": len(events), "next": [e["title"] for e in events[:3]]}

    return api
