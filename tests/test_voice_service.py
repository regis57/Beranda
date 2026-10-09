import httpx
import respx

from beranda.voice_service import _best_station, handle_intent

BASE = "http://127.0.0.1:8080"


def client():
    return httpx.AsyncClient(base_url=BASE)


def test_best_station_picks_the_closest_name():
    stations = [{"name": "France Inter"}, {"name": "France Musique"}, {"name": "Nostalgie"}]
    assert _best_station(stations, "france musique")["name"] == "France Musique"


def test_best_station_refuses_a_poor_match():
    stations = [{"name": "France Inter"}]
    assert _best_station(stations, "something completely different") is None


def test_best_station_with_nothing_saved_or_asked():
    assert _best_station([], "anything") is None
    assert _best_station([{"name": "France Inter"}], "") is None


@respx.mock
async def test_weather_is_read_out(tmp_path):
    respx.get(f"{BASE}/api/state").mock(
        return_value=httpx.Response(200, json={"weather": {"temperature": 18.4, "summary": "partly cloudy"}})
    )
    async with client() as c:
        reply = await handle_intent({"intent": "weather"}, client=c, language="en", timezone="Europe/Paris")
    assert reply == "It's 18 degrees, partly cloudy."


@respx.mock
async def test_weather_unknown_is_handled_gracefully():
    respx.get(f"{BASE}/api/state").mock(return_value=httpx.Response(200, json={"weather": None}))
    async with client() as c:
        reply = await handle_intent({"intent": "weather"}, client=c, language="fr", timezone="Europe/Paris")
    assert reply == "Je n'ai pas la météo pour le moment."


async def test_time_is_read_out_in_the_configured_timezone():
    async with client() as c:
        reply = await handle_intent({"intent": "time"}, client=c, language="en", timezone="Europe/Paris")
    assert reply.startswith("It's ") and reply.endswith(".")


@respx.mock
async def test_radio_play_finds_the_closest_favourite_and_starts_it():
    respx.get(f"{BASE}/api/admin/config").mock(
        return_value=httpx.Response(
            200, json={"config": {"radio": {"stations": [{"name": "France Inter", "url": "http://s"}]}}}
        )
    )
    play = respx.post(f"{BASE}/api/admin/radio-play").mock(return_value=httpx.Response(200, json={}))
    async with client() as c:
        reply = await handle_intent(
            {"intent": "radio_play", "query": "france inter"}, client=c, language="en", timezone="Europe/Paris"
        )
    assert reply == "Playing France Inter."
    assert play.called


@respx.mock
async def test_radio_play_with_no_close_favourite_says_so():
    respx.get(f"{BASE}/api/admin/config").mock(
        return_value=httpx.Response(200, json={"config": {"radio": {"stations": []}}})
    )
    async with client() as c:
        reply = await handle_intent(
            {"intent": "radio_play", "query": "anything"}, client=c, language="en", timezone="Europe/Paris"
        )
    assert reply == "I couldn't find that station in your favourites."


@respx.mock
async def test_radio_stop_calls_the_stop_endpoint():
    stop = respx.post(f"{BASE}/api/admin/radio-stop").mock(return_value=httpx.Response(200, json={}))
    async with client() as c:
        reply = await handle_intent({"intent": "radio_stop"}, client=c, language="en", timezone="Europe/Paris")
    assert reply == "Stopped." and stop.called


@respx.mock
async def test_restart_screen_calls_the_system_action():
    action = respx.post(f"{BASE}/api/admin/system/restart-screen").mock(return_value=httpx.Response(200, json={}))
    async with client() as c:
        reply = await handle_intent({"intent": "restart_screen"}, client=c, language="en", timezone="Europe/Paris")
    assert reply == "Restarting the screen." and action.called


async def test_unrecognised_intent_gets_a_polite_i_dont_understand():
    async with client() as c:
        reply = await handle_intent({"intent": "dance"}, client=c, language="en", timezone="Europe/Paris")
    assert reply == "Sorry, I didn't understand."
