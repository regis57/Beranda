"""TV, from an XMLTV guide the user points us at. Beranda is only ever a *reader*.

There is no free, official, worldwide TV-listings API, and scraping and redistributing a
guide ourselves would touch the sui generis database right that protects EPG data in most
countries. The honest, legal answer: the user finds an XMLTV address for their own country
(their provider, or a community project such as iptv-org/epg) and Beranda reads it, the
same way it reads a calendar's .ics link. We never host, cache forever, or redistribute the
guide itself, only the next few hours of it, for the channels the user picked.
"""

from __future__ import annotations

import gzip
import io
import re
from datetime import UTC, datetime, timedelta

import httpx
from defusedxml.ElementTree import iterparse

USER_AGENT = "Beranda/0.6 (+https://github.com/regis57/Beranda)"
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024  # what we keep in memory: the (compressed) file as downloaded
MAX_DECOMPRESSED_BYTES = 300 * 1024 * 1024  # read as a stream, never held in memory all at once
MAX_CHANNELS = 3000  # big community guides list well over 500 channels
MAX_PROGRAMMES = 3000  # a safety net only: ~20 channels x a few shows each is what we actually keep

_TIME = re.compile(r"^(\d{14})\s*(Z|[+-]\d{4})?$")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _parse_time(raw: str) -> datetime | None:
    """XMLTV timestamps: "20240115200000 +0100" (space before the zone is optional)."""
    m = _TIME.match(raw.strip())
    if not m:
        return None
    try:
        naive = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")  # noqa: DTZ007 - made aware just below
    except ValueError:  # 14 digits but not a real date ("...209000"): one bad line must not sink the guide
        return None
    zone = m.group(2)
    if not zone or zone == "Z":
        return naive.replace(tzinfo=UTC)
    sign = 1 if zone[0] == "+" else -1
    offset = timedelta(hours=int(zone[1:3]), minutes=int(zone[3:5])) * sign
    return (naive - offset).replace(tzinfo=UTC)


class _Capped(io.RawIOBase):
    """Reads from `source` but refuses to go past `limit` bytes (a "zip bomb" guard)."""

    def __init__(self, source, limit: int) -> None:
        self._source, self._left = source, limit

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        data = self._source.read(min(len(buffer), 1 << 20))
        self._left -= len(data)
        if self._left < 0:
            raise ValueError("XMLTV file is too large once decompressed")
        buffer[: len(data)] = data
        return len(data)


def _stream(data: bytes):
    """The guide as a stream of XML, gunzipped on the fly if it is compressed.

    Big guides are 60-120 MB of XML once unpacked: reading them as a stream keeps a small
    Raspberry Pi from ever holding all of it in memory.
    """
    if data[:2] == b"\x1f\x8b":
        return io.BufferedReader(_Capped(gzip.GzipFile(fileobj=io.BytesIO(data)), MAX_DECOMPRESSED_BYTES))
    return io.BytesIO(data)


async def download(url: str) -> bytes:
    """The guide exactly as published (still compressed if it was); `channels` and
    `programmes` unpack it as they read."""
    async with httpx.AsyncClient(
        timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client, client.stream("GET", url) as response:
        response.raise_for_status()
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise ValueError("XMLTV file is too large")
            chunks.append(chunk)
    return b"".join(chunks)


def channels(xml_bytes: bytes) -> list[dict]:
    """Every <channel> the guide declares: {id, name}, for the settings page to pick from."""
    found: dict[str, str] = {}
    for _event, elem in iterparse(_stream(xml_bytes), events=("end",), forbid_dtd=True):
        if _local(elem.tag) != "channel":
            continue  # leave it for its parent to clear: clearing it here would empty it first
        cid = elem.get("id", "").strip()
        name_el = elem.find("display-name")
        name = (name_el.text or "").strip() if name_el is not None and name_el.text else cid
        if cid and cid not in found:
            found[cid] = name
        elem.clear()
        if len(found) >= MAX_CHANNELS:
            break
    return [{"id": cid, "name": name} for cid, name in found.items()]


def programmes(xml_bytes: bytes, channel_ids: set[str], start: datetime, end: datetime) -> list[dict]:
    """<programme>s on the given channels that overlap [start, end), earliest first."""
    names: dict[str, str] = {}
    found: list[dict] = []
    for _event, elem in iterparse(_stream(xml_bytes), events=("end",), forbid_dtd=True):
        tag = _local(elem.tag)
        if tag not in ("channel", "programme"):
            continue  # leave it for its parent to clear, or we'd empty it before reading it
        if tag == "channel":
            cid = elem.get("id", "").strip()
            name_el = elem.find("display-name")
            if cid:
                names[cid] = (name_el.text or "").strip() if name_el is not None and name_el.text else cid
        else:
            cid = elem.get("channel", "").strip()
            if cid in channel_ids:
                begin = _parse_time(elem.get("start", ""))
                # "stop" is optional in XMLTV: with none, assume a short slot rather than drop the show
                finish = _parse_time(elem.get("stop", "")) or (begin + timedelta(minutes=30) if begin else None)
                title_el = elem.find("title")
                title = (title_el.text or "?").strip() if title_el is not None and title_el.text else "?"
                if begin and finish and begin < end and finish > start:
                    found.append({"channel_id": cid, "title": title, "start": begin, "stop": finish})
        elem.clear()
        if len(found) >= MAX_PROGRAMMES:
            break
    for item in found:
        item["channel"] = names.get(item["channel_id"], item["channel_id"])
    found.sort(key=lambda p: (p["start"], p["channel"]))
    return found


def prime_time_picks(found: list[dict], order: list[str], start: datetime, end: datetime) -> list[dict]:
    """One programme per channel: the one that fills most of the [start, end) evening.

    A guide lists many small shows around 20:00 (news, a quiz...); the one a viewer cares about
    is the main programme of the evening, i.e. the one on screen for the longest part of the
    window. Channels come out in the order the user ticked them, so their favourite is first.
    """
    best: dict[str, dict] = {}
    for item in found:
        overlap = (min(item["stop"], end) - max(item["start"], start)).total_seconds()
        if overlap <= 0:
            continue
        current = best.get(item["channel_id"])
        if current is None or overlap > current["_overlap"]:
            best[item["channel_id"]] = {**item, "_overlap": overlap}
    ranked = [best[cid] for cid in order if cid in best]
    ranked += [v for cid, v in best.items() if cid not in order]
    for item in ranked:
        item.pop("_overlap", None)
    return ranked
