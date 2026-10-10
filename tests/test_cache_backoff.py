"""A source that fails is not asked again every minute, and two screens share one fetch."""

import asyncio

from beranda import cache as cache_mod
from beranda.cache import Cache


def test_a_failing_source_is_left_alone_for_a_while(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(cache_mod.time, "time", lambda: clock[0])
    calls = []

    async def ok():
        calls.append("ok")
        return ["headline"]

    async def down():
        calls.append("down")
        raise ConnectionError("429 too many requests")

    async def run():
        c = Cache(tmp_path)
        assert await c.get("news:city", 1800, ok) == (["headline"], False)
        clock[0] += 1801  # the copy is old: try again, it fails, the old copy is shown
        assert await c.get("news:city", 1800, down) == (["headline"], True)
        clock[0] += 60  # a minute later: not asked again
        assert await c.get("news:city", 1800, down) == (["headline"], True)
        assert calls == ["ok", "down"]
        clock[0] += 8 * 60  # after the pause (a quarter of 30 min): asked again, and it works
        assert await c.get("news:city", 1800, ok) == (["headline"], False)
        assert calls == ["ok", "down", "ok"]

    asyncio.run(run())


def test_two_screens_asking_at_once_share_one_fetch(tmp_path):
    calls = []

    async def slow():
        calls.append(1)
        await asyncio.sleep(0.05)
        return "data"

    async def run():
        c = Cache(tmp_path)
        results = await asyncio.gather(c.get("k", 60, slow), c.get("k", 60, slow))
        assert results == [("data", False), ("data", False)] and len(calls) == 1

    asyncio.run(run())
