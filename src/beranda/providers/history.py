""""On this day": historical events for the user's own country, from Wikidata.

Wikidata is a free, community-run knowledge base with a public query service, no account and
no key needed. We ask it two small questions: "which Wikidata item is this ISO country code?"
and "what happened in that country on this calendar day, in history?". Nothing else about the
person is sent - just their country code and today's month and day, the same information the
public holidays already use.
"""

from __future__ import annotations

import httpx

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "Beranda/0.9 (+https://github.com/regis57/Beranda) one small SPARQL query a day"
MAX_EVENTS = 5


async def _query(sparql: str) -> list[dict]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        response = await client.get(SPARQL_URL, params={"query": sparql, "format": "json"})
        response.raise_for_status()
    return response.json()["results"]["bindings"]


async def country_item(country: str) -> str | None:
    """The Wikidata item id (e.g. "Q142" for France) for this ISO 3166-1 alpha-2 code."""
    code = country.strip().upper().replace('"', "")
    if not code:
        return None
    rows = await _query(f'SELECT ?c WHERE {{ ?c wdt:P297 "{code}". }} LIMIT 1')
    if not rows:
        return None
    return rows[0]["c"]["value"].rsplit("/", 1)[-1]


async def on_this_day(item: str, month: int, day: int, language: str, limit: int = MAX_EVENTS) -> list[dict]:
    """Events tied to Wikidata item `item` that happened on this calendar day, earliest first."""
    lang = language.split("-")[0].replace('"', "")
    sparql = f"""
    SELECT ?eventLabel ?date WHERE {{
      ?event wdt:P17 wd:{item}.
      ?event wdt:P585 ?date.
      FILTER(MONTH(?date) = {int(month)} && DAY(?date) = {int(day)})
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang},en". }}
    }}
    ORDER BY ?date
    LIMIT {int(limit)}
    """
    found: list[dict] = []
    for row in await _query(sparql):
        label = row.get("eventLabel", {}).get("value", "")
        raw_date = row.get("date", {}).get("value", "")
        if not label or not raw_date:
            continue
        sign = -1 if raw_date.startswith("-") else 1
        digits = raw_date.lstrip("-").split("-", 1)[0]
        if not digits.isdigit():
            continue
        found.append({"year": sign * int(digits), "label": label})
    return found


async def fetch(country: str, month: int, day: int, language: str) -> list[dict]:
    """Everything this module does, in one call: the country's item, then its "on this day"."""
    item = await country_item(country)
    if item is None:
        return []
    return await on_this_day(item, month, day, language)
