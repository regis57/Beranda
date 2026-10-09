import gzip
from datetime import UTC, datetime

import httpx
import pytest
import respx

from beranda.providers import tv

XML = """<?xml version="1.0" encoding="UTF-8"?>
<tv>
  <channel id="chan1"><display-name>France 2</display-name></channel>
  <channel id="chan2"><display-name>TF1</display-name></channel>
  <programme start="20240115190000 +0100" stop="20240115210000 +0100" channel="chan1">
    <title>Journal</title>
  </programme>
  <programme start="20240115210000 +0100" stop="20240115223000 +0100" channel="chan2">
    <title>Le film du soir</title>
  </programme>
  <programme start="20240115080000 +0100" stop="20240115083000 +0100" channel="chan1">
    <title>Trop tôt</title>
  </programme>
</tv>
""".encode()


def test_channels_lists_every_declared_channel():
    assert tv.channels(XML) == [
        {"id": "chan1", "name": "France 2"},
        {"id": "chan2", "name": "TF1"},
    ]


def test_channels_falls_back_to_the_id_when_there_is_no_name():
    raw = b'<tv><channel id="x"></channel></tv>'
    assert tv.channels(raw) == [{"id": "x", "name": "x"}]


def test_programmes_keeps_only_the_requested_channels_in_the_window():
    start = datetime(2024, 1, 15, 18, 0, tzinfo=UTC)
    end = datetime(2024, 1, 15, 22, 0, tzinfo=UTC)
    found = tv.programmes(XML, {"chan1", "chan2"}, start, end)
    assert [p["title"] for p in found] == ["Journal", "Le film du soir"]
    assert found[0]["channel"] == "France 2"
    assert found[0]["start"] == datetime(2024, 1, 15, 18, 0, tzinfo=UTC)
    assert found[0]["stop"] == datetime(2024, 1, 15, 20, 0, tzinfo=UTC)


def test_programmes_ignores_channels_that_were_not_asked_for():
    start = datetime(2024, 1, 15, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 16, 0, 0, tzinfo=UTC)
    found = tv.programmes(XML, {"chan2"}, start, end)
    assert [p["title"] for p in found] == ["Le film du soir"]


def test_bad_timestamps_are_skipped_not_crashed_on():
    raw = b"""<tv><programme start="nonsense" channel="chan1"><title>?</title></programme></tv>"""
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    assert tv.programmes(raw, {"chan1"}, start, end) == []


@respx.mock
async def test_download_gunzips_a_gz_guide():
    respx.get("https://example.org/guide.xml.gz").mock(
        return_value=httpx.Response(200, content=gzip.compress(XML))
    )
    assert await tv.download("https://example.org/guide.xml.gz") == XML


@respx.mock
async def test_download_plain_guide():
    respx.get("https://example.org/guide.xml").mock(return_value=httpx.Response(200, content=XML))
    assert await tv.download("https://example.org/guide.xml") == XML


@respx.mock
async def test_download_rejects_an_oversized_guide(monkeypatch):
    monkeypatch.setattr(tv, "MAX_DOWNLOAD_BYTES", 10)
    respx.get("https://example.org/guide.xml").mock(return_value=httpx.Response(200, content=XML))
    with pytest.raises(ValueError, match="too large"):
        await tv.download("https://example.org/guide.xml")
