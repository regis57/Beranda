from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest

from beranda.providers import news, news_catalog

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Example</title>
<item><title>First &amp; <b>bold</b> headline</title><link>https://www.example.org/a</link>
<pubDate>Thu, 08 Oct 2026 21:10:00 +0000</pubDate></item>
<item><title>Older one</title><link>https://www.example.org/b</link>
<pubDate>Thu, 08 Oct 2026 08:00:00 +0200</pubDate></item>
<item><title>   </title></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title>
<entry><title type="html">Atom &lt;i&gt;story&lt;/i&gt;</title><link href="https://news.example.com/x"/>
<updated>2026-10-08T22:00:00Z</updated></entry></feed>"""

RDF = b"""<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<item rdf:about="https://allafrica.example/1"><title>RDF item</title><link>https://allafrica.example/1</link>
<dc:date>2026-10-08T20:00:00+00:00</dc:date></item></rdf:RDF>"""

LATIN1 = """<?xml version="1.0" encoding="ISO-8859-1"?>
<rss version="2.0"><channel><item><title>Fête à Sète</title></item></channel></rss>""".encode("latin-1")

BOMB = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>
<rss><channel><item><title>&lol2;</title></item></channel></rss>"""

NOW = datetime(2026, 10, 9, 0, 0, tzinfo=UTC)


def test_rss_titles_are_cleaned_and_sorted():
    items = news.parse(RSS, "Example")
    assert [i["title"] for i in items] == ["First & bold headline", "Older one"]
    assert items[0]["published"] == "2026-10-08T21:10+00:00" and items[1]["published"] == "2026-10-08T06:00+00:00"
    assert items[0]["host"] == "www.example.org" and items[0]["source"] == "Example"


def test_atom_rdf_and_declared_encodings():
    assert news.parse(ATOM, "A")[0]["title"] == "Atom story"
    assert news.parse(ATOM, "A")[0]["host"] == "news.example.com"
    rdf = news.parse(RDF, "AllAfrica")[0]
    assert rdf["title"] == "RDF item" and rdf["published"] == "2026-10-08T20:00+00:00"
    assert news.parse(LATIN1, "x")[0]["title"] == "Fête à Sète"


def test_entity_expansion_attacks_are_refused():
    with pytest.raises(Exception):  # noqa: B017 - defusedxml raises its own error types
        news.parse(BOMB, "evil")


def test_merge_keeps_fresh_unique_and_balanced():
    a = [{"title": f"A{i}", "source": "a", "published": f"2026-10-08T{16 + i}:00+00:00", "host": ""} for i in range(8)]
    b = [{"title": "A1", "source": "b", "published": "2026-10-08T23:00+00:00", "host": ""},  # duplicate title
         {"title": "Old", "source": "b", "published": "2026-09-01T10:00+00:00", "host": ""},  # stale
         {"title": "No date", "source": "b", "published": None, "host": ""}]
    merged = news.merge([a, b], NOW)
    titles = [i["title"] for i in merged]
    assert len([t for t in titles if t.startswith("A")]) == news.PER_SOURCE
    assert "Old" not in titles and titles.count("A1") <= 1 and titles[-1] == "No date"


def test_automatic_choice_prefers_town_country_and_language():
    assert news_catalog.automatic("FR", "fr", "Metz") == ["city", "franceinfo", "lemonde", "france24-fr"]
    br = news_catalog.automatic("BR", "pt-BR", "Recife")
    assert br[0] == "city" and {"g1", "agencia-brasil"} <= set(br) and br[-1] == "bbc-brasil"
    # a country without preset media borrows from its continent
    assert news_catalog.automatic("BJ", "fr", None) == ["allafrica-fr", "rfi-afrique", "france24-fr"]
    # a language without a world source falls back to English
    assert news_catalog.automatic("ZZ", "xx", None) == ["bbc-world"]


def test_catalog_is_consistent():
    ids = [s["id"] for s in news_catalog.SOURCES]
    assert len(ids) == len(set(ids))
    for s in news_catalog.SOURCES:
        assert s["url"].startswith("https://") and s["scope"] in {"world", "national", "region"}
        assert s["scope"] != "national" or s.get("countries")


def test_city_feed_queries_gdelt_in_the_display_language():
    url = news_catalog.city_feed_url("São Paulo", "pt-BR")
    q = parse_qs(urlparse(url).query)
    assert q["query"] == ['"São Paulo" sourcelang:portuguese'] and q["format"] == ["rss"]
    assert "sourcelang" not in parse_qs(urlparse(news_catalog.city_feed_url("Oslo", "xx")).query)["query"][0]
