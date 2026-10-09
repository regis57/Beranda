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


def test_a_timestamp_with_impossible_values_is_skipped():
    assert tv._parse_time("20261008209000 +0000") is None


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
    raw = await tv.download("https://example.org/guide.xml.gz")  # kept as published, unpacked while reading
    assert [c["id"] for c in tv.channels(raw)] == [c["id"] for c in tv.channels(XML)]


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


def test_a_big_guide_is_not_cut_off_before_the_channels_we_want():
    """Regression: the old 200-programme cap stopped reading before reaching later channels."""
    parts = ["<tv>"]
    for n in range(40):  # 40 channels x 10 shows = 400 programmes, ours is the very last channel
        parts.append(f'<channel id="c{n}"><display-name>Chaine {n}</display-name></channel>')
    for n in range(40):
        for h in range(10):
            parts.append(
                f'<programme start="20261008190{h}00 +0000" stop="20261008200{h}00 +0000" channel="c{n}">'
                f"<title>Show {n}-{h}</title></programme>"
            )
    parts.append("</tv>")
    xml = "".join(parts).encode()
    start = datetime(2026, 10, 8, 18, 0, tzinfo=UTC)
    end = datetime(2026, 10, 9, 23, 0, tzinfo=UTC)
    found = tv.programmes(xml, {"c39"}, start, end)
    assert found and all(p["channel_id"] == "c39" for p in found)


def test_more_than_500_channels_are_all_listed():
    xml = ("<tv>" + "".join(f'<channel id="c{n}"><display-name>C{n}</display-name></channel>' for n in range(800)) + "</tv>").encode()
    assert len(tv.channels(xml)) == 800


def test_prime_time_keeps_the_main_programme_of_each_channel_in_the_users_order():
    start = datetime(2026, 10, 8, 18, 0, tzinfo=UTC)
    end = datetime(2026, 10, 8, 21, 0, tzinfo=UTC)

    def show(cid, title, a, b):
        return {
            "channel_id": cid, "channel": cid.upper(), "title": title,
            "start": datetime(2026, 10, 8, a, 0, tzinfo=UTC), "stop": datetime(2026, 10, 8, b, 0, tzinfo=UTC),
        }

    found = [
        show("a", "Journal", 18, 19), show("a", "Film", 19, 21),
        show("b", "Quiz", 18, 19), show("b", "Série", 19, 21),
    ]
    picks = tv.prime_time_picks(found, ["b", "a"], start, end)
    assert [(p["channel"], p["title"]) for p in picks] == [("B", "Série"), ("A", "Film")]


def test_a_compressed_guide_is_read_as_a_stream_and_capped(monkeypatch):
    packed = gzip.compress(XML)
    assert tv.channels(packed) == tv.channels(XML)
    monkeypatch.setattr(tv, "MAX_DECOMPRESSED_BYTES", 50)  # a "zip bomb" is refused, not unpacked
    with pytest.raises(ValueError, match="too large"):
        tv.channels(packed)


def test_a_programme_without_a_stop_time_is_kept():
    xml = b'<tv><channel id="c1"/><programme start="20261008200000 +0000" channel="c1"><title>Film</title></programme></tv>'
    start = datetime(2026, 10, 8, 19, 0, tzinfo=UTC)
    end = datetime(2026, 10, 8, 23, 0, tzinfo=UTC)
    found = tv.programmes(xml, {"c1"}, start, end)
    assert [p["title"] for p in found] == ["Film"]
    assert tv.prime_time_picks(found, ["c1"], start, end)  # not dropped for having no length
