"""A tiny TTL cache that survives restarts and network outages.

The display must keep working when Wi-Fi drops, so every provider call goes through
`Cache.get`: fresh data when possible, the last good copy (flagged stale) when not.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# After a failed fetch (with an old copy to show), wait before asking that source again: a service
# that refuses ("too many requests") must not be asked again every minute by every screen.
RETRY_MIN, RETRY_MAX = 120, 15 * 60


class Cache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._memory: dict[str, tuple[float, Any]] = {}
        self._failed: dict[str, float] = {}  # key -> when to try again
        self._locks: dict[str, asyncio.Lock] = {}
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # read-only SD card, etc.: degrade to memory only
            log.warning("cache directory unusable (%s); using memory only", exc)

    def clear(self) -> int:
        """Forget everything downloaded so far (memory and disk); how many files were deleted.
        The next screen refresh fetches it all again."""
        self._memory.clear()
        self._failed.clear()
        removed = 0
        try:
            for item in self.directory.glob("*.json"):
                try:
                    item.unlink()
                    removed += 1
                except OSError:
                    pass
        except OSError:
            pass
        return removed

    def _path(self, key: str) -> Path:
        return self.directory / (re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".json")

    def _read_disk(self, key: str) -> tuple[float, Any] | None:
        try:
            raw = json.loads(self._path(key).read_text(encoding="utf-8"))
            return float(raw["saved_at"]), raw["value"]
        except (OSError, ValueError, KeyError):
            return None

    def _write_disk(self, key: str, saved_at: float, value: Any) -> None:
        try:
            self._path(key).write_text(
                json.dumps({"saved_at": saved_at, "value": value}), encoding="utf-8"
            )
        except (OSError, TypeError) as exc:
            log.debug("could not persist cache key %s: %s", key, exc)

    async def get(
        self,
        key: str,
        ttl: float,
        fetch: Callable[[], Awaitable[Any]],
    ) -> tuple[Any, bool]:
        """Return (value, stale). Raises only if there is nothing to fall back on."""
        # One fetch at a time per source: two screens asking at the same second share it.
        async with self._locks.setdefault(key, asyncio.Lock()):
            now = time.time()
            entry = self._memory.get(key) or self._read_disk(key)
            if entry and now - entry[0] < ttl:
                self._memory[key] = entry
                return entry[1], False
            if entry and now < self._failed.get(key, 0):
                return entry[1], True  # it failed a moment ago: keep the old copy, do not hammer it
            try:
                value = await fetch()
            except Exception as exc:
                if entry:
                    # Log the exception type only: messages from httpx contain the full URL,
                    # and an ICS "secret address" must never end up in a log file.
                    wait = min(max(ttl / 4, RETRY_MIN), RETRY_MAX)
                    self._failed[key] = now + wait
                    log.warning("fetch %s failed (%s); serving the last good copy, next try in %d min",
                                key, type(exc).__name__, round(wait / 60))
                    self._memory[key] = entry
                    return entry[1], True
                raise
            self._failed.pop(key, None)
            self._memory[key] = (now, value)
            self._write_disk(key, now, value)
            return value, False
