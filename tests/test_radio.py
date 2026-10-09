import httpx
import pytest
import respx

from beranda.providers import radio

STATION = {
    "stationuuid": "abc-123",
    "name": "  Radio Test  ",
    "url": "http://stream.example/low",
    "url_resolved": "http://stream.example/high",
    "favicon": "http://stream.example/icon.png",
    "countrycode": "FR",
    "language": "french,other",
    "tags": "pop,news,talk,extra",
}


@respx.mock
async def test_search_uses_the_first_mirror_that_answers():
    respx.get(f"{radio.MIRRORS[0]}/json/stations/search").mock(return_value=httpx.Response(200, json=[STATION]))
    found = await radio.search(country="fr")
    assert found == [
        {
            "uuid": "abc-123",
            "name": "Radio Test",
            "url": "http://stream.example/high",
            "favicon": "http://stream.example/icon.png",
            "country": "FR",
            "language": "french",
            "tags": ["pop", "news", "talk"],
        }
    ]


@respx.mock
async def test_search_falls_back_to_the_next_mirror():
    respx.get(f"{radio.MIRRORS[0]}/json/stations/search").mock(side_effect=httpx.ConnectError("down"))
    respx.get(f"{radio.MIRRORS[1]}/json/stations/search").mock(return_value=httpx.Response(200, json=[STATION]))
    found = await radio.search(name="test")
    assert found[0]["uuid"] == "abc-123"


@respx.mock
async def test_search_raises_when_every_mirror_fails():
    for mirror in radio.MIRRORS:
        respx.get(f"{mirror}/json/stations/search").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(httpx.HTTPError):
        await radio.search()
