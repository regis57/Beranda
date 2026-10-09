import httpx
import respx

from beranda.providers import history

SPARQL_RESPONSE = {"results": {"bindings": []}}


def _rows(bindings):
    return {"results": {"bindings": bindings}}


@respx.mock
async def test_country_item_reads_the_wikidata_id():
    respx.get(history.SPARQL_URL).mock(
        return_value=httpx.Response(200, json=_rows([{"c": {"value": "http://www.wikidata.org/entity/Q142"}}]))
    )
    assert await history.country_item("fr") == "Q142"


@respx.mock
async def test_country_item_with_no_match_is_none():
    respx.get(history.SPARQL_URL).mock(return_value=httpx.Response(200, json=_rows([])))
    assert await history.country_item("zz") is None


def test_country_item_with_an_empty_code_is_none_without_a_request():
    import asyncio

    assert asyncio.run(history.country_item("")) is None


@respx.mock
async def test_on_this_day_parses_label_and_year():
    respx.get(history.SPARQL_URL).mock(
        return_value=httpx.Response(
            200,
            json=_rows(
                [
                    {"eventLabel": {"value": "Liberation of Paris"}, "date": {"value": "1944-08-25T00:00:00Z"}},
                    {"eventLabel": {"value": "Something ancient"}, "date": {"value": "-0044-08-25T00:00:00Z"}},
                ]
            ),
        )
    )
    found = await history.on_this_day("Q142", 8, 25, "en")
    assert found == [
        {"year": 1944, "label": "Liberation of Paris"},
        {"year": -44, "label": "Something ancient"},
    ]


@respx.mock
async def test_on_this_day_skips_rows_missing_a_label_or_date():
    respx.get(history.SPARQL_URL).mock(
        return_value=httpx.Response(200, json=_rows([{"eventLabel": {"value": "No date"}}]))
    )
    assert await history.on_this_day("Q142", 1, 1, "en") == []


@respx.mock
async def test_fetch_combines_both_queries():
    respx.get(history.SPARQL_URL).mock(
        side_effect=[
            httpx.Response(200, json=_rows([{"c": {"value": "http://www.wikidata.org/entity/Q142"}}])),
            httpx.Response(
                200,
                json=_rows([{"eventLabel": {"value": "Bastille Day"}, "date": {"value": "1789-07-14T00:00:00Z"}}]),
            ),
        ]
    )
    found = await history.fetch("FR", 7, 14, "fr")
    assert found == [{"year": 1789, "label": "Bastille Day"}]


@respx.mock
async def test_fetch_with_an_unknown_country_returns_nothing():
    respx.get(history.SPARQL_URL).mock(return_value=httpx.Response(200, json=_rows([])))
    assert await history.fetch("ZZ", 1, 1, "en") == []
