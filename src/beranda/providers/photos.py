"""The photo tile: a plain folder of pictures, plus two easy ways to fill it.

Where the pictures live
-----------------------
Beranda has its own photo folder (see `default_folder`), so nobody has to invent a path. The
settings page shows where it is and lets you send pictures into it straight from your phone
or computer (`save`), or copy a shared Dropbox folder into it (`sync_dropbox`).

Why not Google Photos, iCloud or Google Drive?
---------------------------------------------
Google closed the door that would let an app read a photo library, Apple never opened one, and
Google Drive needs a private developer account for every user. The practical answer that works
for everybody: on the settings page, tap "Add photos" on your phone - the phone's own picker
can choose pictures from Google Photos, iCloud or Drive. For advanced users, `rclone` or
Syncthing can also keep a folder filled by themselves (then point the settings page at it).
"""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTOS = 500  # a Pi 3B's SD card, not a photo library: keep the listing light
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # one picture; phone photos are typically 2-6 MB
MAX_DROPBOX_BYTES = 400 * 1024 * 1024  # the whole shared folder, as one download
DROPBOX_PREFIX = "dropbox-"  # synced files are tagged so a re-sync never touches your uploads
USER_AGENT = "Beranda/0.12 (+https://github.com/regis57/Beranda)"

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class PhotoError(ValueError):
    """A problem worth telling the person about. `code` lets the settings page say it in their
    own language (link = not a Dropbox shared-folder link, big = too large, bad = not a picture)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def default_folder() -> Path:
    """Beranda's own photo folder: `$BERANDA_PHOTOS` (set by the installer), else under ~/.local."""
    env = os.environ.get("BERANDA_PHOTOS")
    return Path(env) if env else Path.home() / ".local" / "share" / "beranda" / "photos"


def effective_folder(configured: str) -> Path:
    """The folder in use: the one chosen on the settings page, or Beranda's own."""
    return Path(configured).expanduser() if configured.strip() else default_folder()


def list_photos(folder: str | Path) -> list[str]:
    """File names (not paths) of the pictures in `folder`, sorted, newest first.

    An empty or missing folder returns an empty list rather than raising: the photo tile is
    simply hidden until there is something to show.
    """
    if not str(folder):
        return []
    path = Path(folder).expanduser()
    if not path.is_dir():
        return []
    files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONS]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return [f.name for f in files[:MAX_PHOTOS]]


def resolve(folder: str | Path, name: str) -> Path | None:
    """The path to serve for `name`, or None if it would escape `folder` or doesn't exist.

    `name` comes from a URL path segment, so it is never trusted as-is: resolving it and
    checking it is still inside `folder` is what stops `..` tricks from reading other files.
    """
    if not str(folder) or not name or "/" in name or "\\" in name:
        return None
    base = Path(folder).expanduser().resolve()
    candidate = (base / name).resolve()
    if candidate.parent != base or candidate.suffix.lower() not in EXTENSIONS:
        return None
    return candidate if candidate.is_file() else None


def safe_name(raw: str) -> str:
    """A harmless file name made from whatever the phone called the picture."""
    stem, dot, ext = Path(raw.replace("\\", "/").split("/")[-1]).name.rpartition(".")
    if not dot:
        stem, ext = ext, ""
    stem = _SAFE_NAME.sub("-", stem).strip("-.")[:60] or "photo"
    return f"{stem}.{ext.lower()}" if ext else stem


def _looks_like_picture(data: bytes) -> bool:
    """Check the first bytes, not just the file name: a renamed text file is not a photo."""
    if data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n" or data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def save(folder: Path, raw_name: str, data: bytes) -> str:
    """Store one uploaded picture and return the name it was saved under.

    Raises ValueError (with a plain-language message) if it is too big or not a picture.
    """
    if not data:
        raise PhotoError("bad", "the file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise PhotoError("big", "that picture is too big (15 MB at most)")
    name = safe_name(raw_name)
    if Path(name).suffix.lower() not in EXTENSIONS:
        raise PhotoError("bad", "only JPG, PNG, WebP and GIF pictures can be added")
    if not _looks_like_picture(data):
        raise PhotoError("bad", "that file is not a picture")
    folder.mkdir(parents=True, exist_ok=True)
    if name.startswith(DROPBOX_PREFIX):
        name = "my-" + name  # keep the prefix for the Dropbox copy only
    target = folder / name
    counter = 1
    while target.exists():  # never overwrite: the same camera name can come back
        target = folder / f"{Path(name).stem}-{counter}{Path(name).suffix}"
        counter += 1
    target.write_bytes(data)
    return target.name


def delete(folder: Path, name: str) -> bool:
    path = resolve(folder, name)
    if path is None:
        return False
    path.unlink()
    return True


def dropbox_download_url(link: str) -> str:
    """Turn a Dropbox shared-folder link into the address that downloads it as one .zip."""
    parsed = urlparse(link.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not (host == "dropbox.com" or host.endswith(".dropbox.com")):
        raise PhotoError("link", "that is not a Dropbox link")
    query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "dl"] + [("dl", "1")]
    return urlunparse(parsed._replace(scheme="https", query=urlencode(query)))


async def sync_dropbox(link: str, folder: Path) -> dict:
    """Copy the pictures of a Dropbox shared folder into `folder` (tagged `dropbox-`).

    Pictures that were removed from the Dropbox folder are removed here too, but only the
    ones this function created: pictures you added by hand are never touched.
    Returns {"added": n, "removed": n, "total": n}.
    """
    url = dropbox_download_url(link)
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as tmp:
        async with httpx.AsyncClient(
            timeout=60, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client, client.stream("GET", url) as response:
            response.raise_for_status()
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_DROPBOX_BYTES:
                    raise PhotoError("big", "that Dropbox folder is too big (400 MB at most)")
                tmp.write(chunk)
        tmp.seek(0)
        return extract_zip(tmp, folder)


def extract_zip(fileobj, folder: Path) -> dict:
    """Copy the pictures inside a .zip into `folder`, one at a time (kind to a Pi's memory).

    Files get the `dropbox-` tag; tagged files that are no longer in the zip are removed.
    Returns {"added": n, "removed": n, "total": n}.
    """
    try:
        archive = zipfile.ZipFile(fileobj)
    except zipfile.BadZipFile as exc:
        raise PhotoError("link", "Dropbox did not return a folder - is the link a shared folder?") from exc
    folder.mkdir(parents=True, exist_ok=True)
    kept: set[str] = set()
    added = 0
    with archive:
        infos = [i for i in archive.infolist() if not i.is_dir() and Path(i.filename).suffix.lower() in EXTENSIONS]
        infos.sort(key=lambda i: i.date_time, reverse=True)
        for info in infos[:MAX_PHOTOS]:
            name = DROPBOX_PREFIX + safe_name(info.filename)
            if info.file_size > MAX_UPLOAD_BYTES or name in kept:
                continue
            target = folder / name
            if target.exists() and target.stat().st_size == info.file_size:
                kept.add(name)
                continue
            data = archive.read(info)
            if not _looks_like_picture(data):
                continue
            part = target.with_suffix(target.suffix + ".part")
            part.write_bytes(data)
            os.replace(part, target)
            kept.add(name)
            added += 1
    removed = 0
    for old in folder.glob(f"{DROPBOX_PREFIX}*"):
        if old.is_file() and old.name not in kept and old.suffix.lower() in EXTENSIONS:
            old.unlink()
            removed += 1
    return {"added": added, "removed": removed, "total": len(kept)}
