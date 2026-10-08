"""Headlines from RSS and Atom feeds: download, read, merge, keep the freshest.

Feeds are untrusted input. We parse them with defusedxml (no entity tricks), cap their size,
keep only the title, the link's host, the date and the medium's name, and strip any markup.
"""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx
from defusedxml import ElementTree

USER_AGENT = "Beranda/0.3 (+https://github.com/regis57/Beranda)"
MAX_FEED_BYTES = 3 * 1024 * 1024
MAX_AGE = timedelta(days=3)
PER_SOURCE = 5
TOTAL = 24

_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def _local(tag: str) -> str:
    """'{http://www.w3.org/2005/Atom}entry' -> 'entry'."""
    return tag.rsplit("}", 1)[-1].lower()


def _child(node, *names: str):
    for child in node:
        if _local(child.tag) in names:
            return child
    return None


def _text(node) -> str:
    if node is None:
        return ""
    raw = "".join(node.itertext())
    return _SPACES.sub(" ", html.unescape(_TAGS.sub(" ", raw))).strip()


def _date(text: str) -> datetime | None:
    text = text.strip()
    if not text:
        return None
    try:
        value = parsedate_to_datetime(text)  # RSS: "Wed, 07 Oct 2026 22:14:58 +0000"
    except (TypeError, ValueError, IndexError):
        try:
            value = datetime.fromisoformat(text)  # Atom / Dublin Core (Python 3.11 reads "Z")
        except ValueError:
            # GDELT writes "20261008T101500Z"
            try:
                value = datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            except ValueError:
                return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def parse(xml_text: bytes | str, source_name: str) -> list[dict]:
    """Items of an RSS 2.0, RSS 1.0 (RDF) or Atom feed, newest first."""
    root = ElementTree.fromstring(xml_text)
    items = [el for el in root.iter() if _local(el.tag) in {"item", "entry"}]
    out = []
    for item in items:
        title = _text(_child(item, "title"))
        if not title:
            continue
        link_node = _child(item, "link")
        link = ""
        if link_node is not None:
            link = (link_node.get("href") or _text(link_node)).strip()
        when = _date(_text(_child(item, "pubdate", "published", "updated", "date", "seendate")))
        out.append({
            "title": title[:220],
            "source": source_name,
            "published": when.astimezone(UTC).isoformat(timespec="minutes") if when else None,
            "host": httpx.URL(link).host if link.startswith("http") else "",
        })
    out.sort(key=lambda i: i["published"] or "", reverse=True)
    return out


async def fetch(url: str) -> bytes:
    async with httpx.AsyncClient(
        timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client, client.stream("GET", url) as response:
        response.raise_for_status()
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_FEED_BYTES:
                raise ValueError("feed too large")
            chunks.append(chunk)
    # Bytes, not text: the XML declaration says which encoding the feed uses.
    return b"".join(chunks)


def merge(per_source: list[list[dict]], now: datetime) -> list[dict]:
    """Freshest first, at most PER_SOURCE per medium, no duplicate titles, nothing stale."""
    seen: set[str] = set()
    pool = []
    for items in per_source:
        kept = 0
        for item in items:
            key = re.sub(r"\W+", "", item["title"].lower())
            if key in seen:
                continue
            if item["published"]:
                age = now - datetime.fromisoformat(item["published"])
                if age > MAX_AGE:
                    continue
            seen.add(key)
            pool.append(item)
            kept += 1
            if kept >= PER_SOURCE:
                break
    pool.sort(key=lambda i: i["published"] or "", reverse=True)
    return pool[:TOTAL]
