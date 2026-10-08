import httpx
import pytest
import respx

from beranda.providers import weather


def payload(rain: list[float] | None = None, now: str = "2026-10-08T22:00") -> dict:
    """A response shaped like Open-Meteo's, trimmed to what we read."""
    times = [f"2026-10-08T21:{m:02d}" for m in (0, 15, 30, 45)] + [
        f"2026-10-08T{h}:{m:02d}" for h in (22, 23) for m in (0, 15, 30, 45)
    ]
    rain = rain if rain is not None else [0.0] * 8
    return {
        "current": {
            "time": now, "temperature_2m": 10.6, "apparent_temperature": 8.4,
            "relative_humidity_2m": 80, "precipitation": 0.0, "weather_code": 3,
            "wind_speed_10m": 13.7, "wind_direction_10m": 220, "is_day": 0,
        },
        "minutely_15": {"time": times, "precipitation": [0.0] * 4 + rain},  # 4 past, 8 future
        "daily": {
            "time": ["2026-10-08", "2026-10-09"],
            "weather_code": [3, 61],
            "temperature_2m_max": [14.2, 12.6], "temperature_2m_min": [8.1, 9.4],
            "precipitation_sum": [0.4, 4.25], "precipitation_probability_max": [35, 80],
            "sunrise": ["2026-10-08T07:45", "2026-10-09T07:47"],
            "sunset": ["2026-10-08T18:59", "2026-10-09T18:57"],
            "uv_index_max": [2.1, 1.4],
        },
    }


def test_parse_rounds_and_maps_the_current_conditions():
    out = weather.parse(payload())
    assert out["current"]["temp"] == 11 and out["current"]["feels"] == 8
    assert out["current"]["is_day"] is False
    assert out["units"] == {"temp": "°C", "wind": "km/h", "precip": "mm"}
    assert [d["tmax"] for d in out["daily"]] == [14, 13]
    assert out["daily"][1]["pop"] == 80 and out["daily"][1]["precip"] == 4.2


def test_dry_next_two_hours():
    rain = weather.parse(payload())["rain"]
    assert rain["raining_now"] is False
    assert rain["starts_in_min"] is None and rain["stops_in_min"] is None
    assert len(rain["intervals"]) == 8


def test_rain_that_starts_later():
    rain = weather.parse(payload([0, 0, 0, 0.3, 0.6, 0.2, 0, 0]))["rain"]
    assert rain["starts_in_min"] == 45 and rain["raining_now"] is False


def test_rain_that_stops_soon():
    rain = weather.parse(payload([0.5, 0.4, 0.1, 0, 0, 0, 0, 0]))["rain"]
    assert rain["raining_now"] is True and rain["stops_in_min"] == 45


def test_rain_all_window_long():
    rain = weather.parse(payload([0.4] * 8))["rain"]
    assert rain["raining_now"] is True and rain["stops_in_min"] is None


def test_trace_amounts_do_not_count_as_rain():
    rain = weather.parse(payload([0.04, 0.05, 0, 0, 0, 0, 0, 0]))["rain"]
    assert rain["raining_now"] is False and rain["starts_in_min"] is None


def test_missing_minutely_block_is_tolerated():
    data = payload()
    del data["minutely_15"]
    rain = weather.parse(data)["rain"]
    assert rain["intervals"] == [] and rain["raining_now"] is False


def test_imperial_parameters():
    params = weather.build_params(30.0, -97.0, "imperial")
    assert params["temperature_unit"] == "fahrenheit" and params["wind_speed_unit"] == "mph"
    assert weather.parse(payload(), "imperial")["units"]["temp"] == "°F"


@respx.mock
async def test_fetch_sends_a_polite_request_and_parses():
    route = respx.get(weather.URL).mock(return_value=httpx.Response(200, json=payload()))
    out = await weather.fetch(49.12, 6.18, "metric")
    assert out["source"] == "Open-Meteo"
    request = route.calls.last.request
    assert "Beranda" in request.headers["user-agent"]
    assert request.url.params["latitude"] == "49.12"


@respx.mock
async def test_fetch_raises_on_server_error():
    respx.get(weather.URL).mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        await weather.fetch(49.12, 6.18, "metric")
