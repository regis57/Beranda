"""Regression tests for the TV guide reader and the radio search."""

import gzip
from datetime import UTC, datetime

import httpx
import pytest
import respx
from defusedxml import DefusedXmlException

from beranda.providers import radio, tv

DOCTYPE_GUIDE = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv><channel id="a"><display-name>Chaine A</display-name></channel>
<programme start="20240115190000 +0000" stop="20240115200000 +0000" channel="a"><title>Show</title></programme>
</tv>"""

DAY = (datetime(2024, 1, 15, tzinfo=UTC), datetime(2024, 1, 16, tzinfo=UTC))


def test_guide_with_the_standard_xmltv_doctype_is_read():
    assert tv.channels(DOCTYPE_GUIDE) == [{"id": "a", "name": "Chaine A"}]
    assert tv.channels(gzip.compress(DOCTYPE_GUIDE)) == [{"id": "a", "name": "Chaine A"}]
    shows = tv.programmes(DOCTYPE_GUIDE, {"a"}, *DAY)
    assert [s["title"] for s in shows] == ["Show"]


@pytest.mark.parametrize(
    "doc",
    [
        b'<?xml version="1.0"?><!DOCTYPE tv [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]>'
        b'<tv><channel id="x"><display-name>&b;</display-name></channel></tv>',
        b'<?xml version="1.0"?><!DOCTYPE tv [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
        b'<tv><channel id="x"><display-name>&e;</display-name></channel></tv>',
    ],
)
def test_entity_tricks_are_still_refused(doc):
    with pytest.raises(DefusedXmlException):
        tv.channels(doc)
    with pytest.raises(DefusedXmlException):
        tv.programmes(doc, {"x"}, *DAY)


def test_channel_list_stops_reading_at_the_first_programme():
    # A broken tail after the first programme proves the rest of the guide is never parsed,
    # so the programmes are not all kept in memory under the root just to list channels.
    guide = b'<tv><channel id="a"><display-name>A</display-name></channel><programme channel="a"></programme><oops'
    assert tv.channels(guide) == [{"id": "a", "name": "A"}]


def _capture(stations):
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return httpx.Response(200, json=stations)

    respx.get(f"{radio.MIRRORS[0]}/json/stations/search").mock(side_effect=handler)
    return seen


@respx.mock
@pytest.mark.parametrize(
    ("code", "name"), [("de", "german"), ("es", "spanish"), ("pt-BR", "portuguese"), ("zh-TW", "chinese")]
)
async def test_language_code_is_sent_as_the_language_name(code, name):
    seen = _capture([])
    await radio.search(language=code)
    assert seen["language"] == name


@respx.mock
async def test_unknown_language_code_sends_no_language_filter():
    seen = _capture([])
    await radio.search(language="xx")
    assert "language" not in seen


@respx.mock
async def test_station_prefers_an_https_address_and_says_so():
    _capture(
        [
            {"stationuuid": "1", "name": "A", "url": "https://s/a", "url_resolved": "http://s/a"},
            {"stationuuid": "2", "name": "B", "url": "http://s/b", "url_resolved": "http://s/b2"},
        ]
    )
    a, b = await radio.search()
    assert a["url"] == "https://s/a" and a["https"] is True
    assert b["url"] == "http://s/b2" and b["https"] is False
