#!/usr/bin/env python3
"""Check every news feed of the catalog: does it answer, and does it parse as RSS/Atom?

Run by a weekly GitHub Actions job (and on pull requests that touch the catalog), because a
feed address can change without notice. Prints one line per feed and exits 1 if any fails.

    python scripts/check_feeds.py            # all feeds
    python scripts/check_feeds.py g1 nhk     # only these ids
"""

from __future__ import annotations

import asyncio
import os
import sys

from beranda.providers import news, news_catalog


async def check(source: dict, gate: asyncio.Semaphore) -> tuple[dict, str | None, int]:
    async with gate:
        try:
            items = news.parse(await news.fetch(source["url"]), source["name"])
        except Exception as exc:  # noqa: BLE001
            return source, f"{type(exc).__name__}: {str(exc)[:80]}", 0
    return source, None if items else "no items", len(items)


async def main(ids: list[str]) -> int:
    sources = [s for s in news_catalog.SOURCES if not ids or s["id"] in ids]
    sources.append({"id": "city(Paris)", "name": "GDELT", "url": news_catalog.city_feed_url("Paris", "fr")})
    gate = asyncio.Semaphore(8)
    results = await asyncio.gather(*(check(s, gate) for s in sources))
    failed = 0
    for source, error, count in results:
        if error:
            failed += 1
            print(f"FAIL  {source['id']:<22} {error}  <{source['url']}>")
        else:
            print(f"ok    {source['id']:<22} {count:>3} items")
    print(f"\n{len(results) - failed}/{len(results)} feeds answer.")
    if os.environ.get("GITHUB_ACTIONS"):
        # One annotation each, readable in the pull request without opening the raw log.
        bad = [f"{s['id']}: {e}" for s, e, _ in results if e]
        good = [f"{s['id']} ({n})" for s, e, n in results if not e]
        print(f"::notice title={len(good)} feeds answer::" + ", ".join(good))
        # GitHub keeps only a few lines per annotation: one annotation per four failures.
        for i in range(0, len(bad), 4):
            print(f"::error title=feeds fail ({i + 1}-{min(i + 4, len(bad))} of {len(bad)})::" + "%0A".join(bad[i : i + 4]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))
