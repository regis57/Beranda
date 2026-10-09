"""Weather from Open-Meteo: free, no API key, worldwide (CC BY 4.0, attribution in README).

`parse` is a pure function so it can be tested against recorded payloads without a network.
"""

from __future__ import annotations

from datetime import datetime

import httpx

URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "Beranda/0.4 (+https://github.com/regis57/Beranda)"
RAIN_THRESHOLD_MM = 0.1  # per 15 minutes: below this we call it dry
RAIN_WINDOW = 8  # 8 x 15 min = the next two hours


def _units(units: str) -> dict:
    if units == "imperial":
        return {"temp": "°F", "wind": "mph", "precip": "in"}
    return {"temp": "°C", "wind": "km/h", "precip": "mm"}


def build_params(latitude: float, longitude: float, units: str) -> dict:
    metric = units != "imperial"
    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "current": (
            "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,"
            "weather_code,wind_speed_10m,wind_direction_10m,is_day"
        ),
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "minutely_15": "precipitation",
        "forecast_minutely_15": RAIN_WINDOW + 4,
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
            "precipitation_probability_max,sunrise,sunset,uv_index_max"
        ),
        "forecast_days": 7,
        "temperature_unit": "celsius" if metric else "fahrenheit",
        "wind_speed_unit": "kmh" if metric else "mph",
        "precipitation_unit": "mm" if metric else "inch",
    }


async def fetch(latitude: float, longitude: float, units: str) -> dict:
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": USER_AGENT}) as client:
        response = await client.get(URL, params=build_params(latitude, longitude, units))
        response.raise_for_status()
        return parse(response.json(), units)


def _rain(payload: dict, now_local: str) -> dict:
    """The next two hours of rain, in 15-minute steps, and when it starts/stops."""
    block = payload.get("minutely_15") or {}
    times = block.get("time") or []
    values = block.get("precipitation") or []
    start = next((i for i, t in enumerate(times) if t >= now_local), 0)
    window = [round(float(v or 0.0), 2) for v in values[start : start + RAIN_WINDOW]]

    wet = [v >= RAIN_THRESHOLD_MM for v in window]
    starts_in = stops_in = None
    if window:
        if wet[0]:
            # raining now: when does it stop?
            stops_in = next((i * 15 for i, w in enumerate(wet) if not w), None)
        else:
            starts_in = next((i * 15 for i, w in enumerate(wet) if w), None)
    return {
        "intervals": window,
        "raining_now": bool(window and wet[0]),
        "starts_in_min": starts_in,
        "stops_in_min": stops_in,
    }


HOURLY_COUNT = 24


def _hourly(payload: dict, now_local: str) -> list[dict]:
    """The next 24 hours, one entry per hour starting with the current one (for the graph)."""
    block = payload.get("hourly") or {}
    times = block.get("time") or []
    if not times:
        return []
    this_hour = now_local[:13]  # "2026-10-09T21"
    start = next((i for i, t in enumerate(times) if t[:13] >= this_hour), 0)
    out = []
    for i in range(start, min(start + HOURLY_COUNT, len(times))):
        temp = (block.get("temperature_2m") or [None] * len(times))[i]
        if temp is None:
            continue
        out.append(
            {
                "time": times[i],
                "temp": round(temp, 1),
                "precip": round(float((block.get("precipitation") or [0] * len(times))[i] or 0.0), 2),
                "wind": round(float((block.get("wind_speed_10m") or [0] * len(times))[i] or 0.0)),
            }
        )
    return out


def parse(payload: dict, units: str = "metric") -> dict:
    """Normalise an Open-Meteo response to what the display needs."""
    cur = payload["current"]
    daily = payload["daily"]

    days = []
    for i, day in enumerate(daily["time"]):
        days.append(
            {
                "date": day,
                "code": daily["weather_code"][i],
                "tmax": round(daily["temperature_2m_max"][i]),
                "tmin": round(daily["temperature_2m_min"][i]),
                "precip": round(daily["precipitation_sum"][i] or 0.0, 1),
                "pop": daily["precipitation_probability_max"][i],
                "sunrise": daily["sunrise"][i],
                "sunset": daily["sunset"][i],
                "uv": daily["uv_index_max"][i],
            }
        )

    return {
        "current": {
            "time": cur["time"],
            "temp": round(cur["temperature_2m"]),
            "feels": round(cur["apparent_temperature"]),
            "humidity": cur["relative_humidity_2m"],
            "wind": round(cur["wind_speed_10m"]),
            "wind_dir": cur["wind_direction_10m"],
            "code": cur["weather_code"],
            "is_day": bool(cur["is_day"]),
            "precip": cur["precipitation"],
        },
        "rain": _rain(payload, cur["time"]),
        "hourly": _hourly(payload, cur["time"]),
        "daily": days,
        "units": _units(units),
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "Open-Meteo",
    }
