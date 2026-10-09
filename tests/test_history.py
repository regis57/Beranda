import httpx
import respx

from beranda.providers import history

FEED = {
    "selected": [{"text": "A highlight", "year": 1944, "pages": []}],
    "events": [
        {"text": "Old thing", "year": 1200},
        {"text": "Recent   thing\n with   spaces", "year": 1990},
        {"text": "A highlight", "year": 1944},  # also in the general list: shown once
        {"text": "", "year": 2000},  # no text: skipped
        {"text": "No year"},  # no year: skipped
    ],
}


def test_parse_puts_highlights_first_then_recent_history_and_cleans_text():
    assert history.parse(FEED) == [
        {"year": 1944, "text": "A highlight"},
        {"year": 1990, "text": "Recent thing with spaces"},
        {"year": 1200, "text": "Old thing"},
    ]


def test_parse_shortens_long_text_and_respects_the_limit():
    feed = {"events": [{"text": f"{i}" + "x" * 500, "year": 1900 + i} for i in range(10)]}
    found = history.parse(feed, limit=3)
    assert len(found) == 3 and all(len(e["text"]) <= history.MAX_TEXT for e in found)


def test_parse_of_an_empty_or_odd_feed_is_empty():
    assert history.parse({}) == []
    assert history.parse({"selected": None, "events": None}) == []


@respx.mock
async def test_fetch_reads_the_language_edition_of_the_user():
    route = respx.get(history.FEED_URL.format(lang="fr", month=10, day=9)).mock(
        return_value=httpx.Response(200, json=FEED)
    )
    found = await history.fetch("fr", 10, 9)
    assert route.called and found[0]["text"] == "A highlight"


@respx.mock
async def test_fetch_uses_the_base_language_of_a_regional_code():
    route = respx.get(history.FEED_URL.format(lang="pt", month=1, day=2)).mock(
        return_value=httpx.Response(200, json=FEED)
    )
    await history.fetch("pt-BR", 1, 2)
    assert route.called


@respx.mock
async def test_fetch_falls_back_to_english_when_the_language_has_no_feed():
    respx.get(history.FEED_URL.format(lang="sw", month=3, day=4)).mock(return_value=httpx.Response(404))
    respx.get(history.FEED_URL.format(lang="en", month=3, day=4)).mock(return_value=httpx.Response(200, json=FEED))
    assert (await history.fetch("sw", 3, 4))[0]["year"] == 1944


@respx.mock
async def test_fetch_lets_a_server_error_through_so_the_cache_can_keep_the_old_answer():
    respx.get(history.FEED_URL.format(lang="fr", month=5, day=6)).mock(return_value=httpx.Response(500))
    try:
        await history.fetch("fr", 5, 6)
    except httpx.HTTPStatusError:
        return
    raise AssertionError("a 500 must not be mistaken for 'nothing happened today'")
