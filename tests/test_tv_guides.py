import httpx
import respx

from beranda.providers import tv_guides


def test_candidates_are_built_for_the_country_in_the_right_case():
    urls = [c["url"] for c in tv_guides.candidates("fr")]
    assert "https://iptv-epg.org/files/epg-fr.xml.gz" in urls
    assert "https://epg.pw/xmltv/epg_FR.xml.gz" in urls
    assert urls[0].startswith("https://xmltvfr.fr/")  # the France-only community guide comes first


def test_a_country_with_no_special_name_gets_the_worldwide_sources_only():
    names = {c["name"] for c in tv_guides.candidates("JP")}
    assert names == {"iptv-epg.org", "epg.pw"}


def test_nonsense_country_codes_give_nothing():
    for bad in ("", "F", "FRA", "12", None):
        assert tv_guides.candidates(bad) == []


@respx.mock
async def test_available_keeps_real_guides_and_drops_dead_or_fake_ones():
    options = tv_guides.candidates("DE")
    gz, plain, html, dead = options[0], options[1], options[2], options[3:]
    respx.get(gz["url"]).mock(return_value=httpx.Response(200, content=b"\x1f\x8b\x08" + b"0" * 50))
    respx.get(plain["url"]).mock(return_value=httpx.Response(200, content=b'<?xml version="1.0"?><tv/>'))
    respx.get(html["url"]).mock(return_value=httpx.Response(200, content=b"<!doctype html><html>404</html>"))
    for option in dead:
        respx.get(option["url"]).mock(side_effect=httpx.ConnectError("down"))
    found = await tv_guides.available("DE")
    assert [g["url"] for g in found] == [gz["url"], plain["url"]]


async def test_available_for_an_unknown_country_makes_no_request():
    assert await tv_guides.available("") == []
