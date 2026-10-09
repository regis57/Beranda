"""Finding a TV guide for the person's country, so nobody has to hunt for a link.

An "XMLTV guide" is just a file listing what is on each TV channel. Several volunteer
projects publish one per country for free. This module knows the usual addresses, tries
each for the chosen country, and keeps only the ones that really answer *right now* - the
settings page then offers those as one-tap buttons.

Beranda only ever reads these files (see `tv.py`); it never copies or republishes them.
Honest limit: these projects are run by volunteers and can move or disappear, which is why
every address is tested live instead of being trusted, and why the page still lets you paste
any other guide address by hand.
"""

from __future__ import annotations

import asyncio

import httpx

USER_AGENT = "Beranda/0.12 (+https://github.com/regis57/Beranda)"

# {cc} = the two-letter country code, lower case; {CC} = upper case.
# Only worldwide, one-file-per-country sources go here; a country-specific source is added
# in COUNTRY_EXTRAS. Ordered by how often each has been dependable.
PER_COUNTRY = (
    ("iptv-epg.org", "https://iptv-epg.org/files/epg-{cc}.xml.gz"),
    ("epg.pw", "https://epg.pw/xmltv/epg_{CC}.xml.gz"),
    ("epg.pw", "https://epg.pw/xmltv/epg_{CC}.xml"),
    ("open-epg.com", "https://www.open-epg.com/files/{name}1.xml.gz"),
)

# Community guides built for just one country.
COUNTRY_EXTRAS: dict[str, tuple[tuple[str, str], ...]] = {
    "FR": (("xmltvfr.fr", "https://xmltvfr.fr/xmltv/xmltv.xml.gz"),),
}

# open-epg.com names its files by country name (france1.xml.gz); only the common ones.
OPEN_EPG_NAMES = {
    "FR": "france", "GB": "unitedkingdom", "DE": "germany", "ES": "spain", "IT": "italy",
    "PT": "portugal", "BE": "belgium", "CH": "switzerland", "NL": "netherlands",
    "US": "usa", "CA": "canada", "BR": "brazil", "MX": "mexico", "IE": "ireland",
}

PROJECT_PAGE = "https://github.com/iptv-org/epg"  # for people who want to build their own


def candidates(country: str) -> list[dict]:
    """Every address worth trying for this country: [{"name", "url"}], best guess first."""
    code = (country or "").strip().upper()
    if len(code) != 2 or not code.isalpha():
        return []
    found = [{"name": name, "url": url} for name, url in COUNTRY_EXTRAS.get(code, ())]
    for name, template in PER_COUNTRY:
        if "{name}" in template:
            if code not in OPEN_EPG_NAMES:
                continue
            url = template.format(name=OPEN_EPG_NAMES[code])
        else:
            url = template.format(cc=code.lower(), CC=code)
        found.append({"name": name, "url": url})
    return found


async def _answers(client: httpx.AsyncClient, url: str) -> bool:
    """True if the address replies with a real file (we read only its first bytes)."""
    try:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                return False
            async for chunk in response.aiter_bytes():
                head = chunk[:200].lstrip()
                # a guide is XML, or gzip-compressed XML; an HTML error page is neither
                return head[:2] == b"\x1f\x8b" or head[:5] == b"<?xml" or head[:3] == b"<tv"
            return False
    except httpx.HTTPError:
        return False


async def available(country: str) -> list[dict]:
    """The candidates for `country` that answer right now, in the same order."""
    options = candidates(country)
    if not options:
        return []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        alive = await asyncio.gather(*(_answers(client, o["url"]) for o in options))
    return [o for o, ok in zip(options, alive, strict=True) if ok]
