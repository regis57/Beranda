"""The photo carousel: a local folder, nothing else.

No cloud photo API is wired in on purpose — Google Photos closed the door that would let an
app read a whole library, and Amazon/iCloud never opened one. The honest, durable answer is
a plain folder that something else keeps full: `rclone` (Google Drive, Dropbox, OneDrive,
pCloud, S3, and about fifty more) or Syncthing (a phone's own camera roll, no cloud account
at all). Beranda only ever reads image files that are already sitting in that folder.
"""

from __future__ import annotations

from pathlib import Path

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTOS = 500  # a Pi 3B's SD card, not a photo library: keep the listing light


def list_photos(folder: str) -> list[str]:
    """File names (not paths) of the pictures in `folder`, sorted, newest first.

    An empty or missing folder returns an empty list rather than raising: the carousel is
    simply off until the user points it at a real folder (or rclone/Syncthing fill it in).
    """
    if not folder:
        return []
    path = Path(folder).expanduser()
    if not path.is_dir():
        return []
    files = [f for f in path.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONS]
    files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return [f.name for f in files[:MAX_PHOTOS]]


def resolve(folder: str, name: str) -> Path | None:
    """The path to serve for `name`, or None if it would escape `folder` or doesn't exist.

    `name` comes from a URL path segment, so it is never trusted as-is: resolving it and
    checking it is still inside `folder` is what stops `..` tricks from reading other files.
    """
    if not folder or not name or "/" in name or "\\" in name:
        return None
    base = Path(folder).expanduser().resolve()
    candidate = (base / name).resolve()
    if candidate.parent != base or candidate.suffix.lower() not in EXTENSIONS:
        return None
    return candidate if candidate.is_file() else None
