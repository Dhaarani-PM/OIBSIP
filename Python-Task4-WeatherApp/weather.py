from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from api import WeatherAPIError, get_current_weather, get_forecast
from utils import local_datetime, now_in_city


TARGET_HOURS = (0, 3, 6, 9, 12, 15, 18, 21)


MAX_SLOT_DISTANCE_SECONDS = 95 * 60


def _weather_condition(item: dict[str, Any]) -> dict[str, Any]:
    weather_items = item.get("weather")

    if not isinstance(weather_items, list) or not weather_items:
        raise WeatherAPIError("Weather data is missing a weather condition.")

    condition = weather_items[0]

    if not isinstance(condition, dict):
        raise WeatherAPIError("Weather condition data is malformed.")

    return {
        "id": condition.get("id", 0),
        "main": condition.get("main", "Unknown"),
        "description": condition.get("description", "Unknown"),
        "icon": condition.get("icon", ""),
    }


def process_current(data: dict[str, Any]) -> dict[str, Any]:
    main = data.get("main")
    wind = data.get("wind", {})
    system = data.get("sys", {})

    if not isinstance(main, dict) or "temp" not in main:
        raise WeatherAPIError("Current weather data is incomplete.")

    if not isinstance(wind, dict):
        wind = {}

    if not isinstance(system, dict):
        system = {}

    return {
        "city": data.get("name", "Unknown location"),
        "country": system.get("country", ""),
        "timestamp": int(data.get("dt", 0)),
        "timezone_offset": int(data.get("timezone", 0)),
        "temperature": float(main["temp"]),
        "feels_like": float(main.get("feels_like", main["temp"])),
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "wind_speed": wind.get("speed"),
        "sunrise": int(system.get("sunrise", 0)),
        "sunset": int(system.get("sunset", 0)),
        "condition": _weather_condition(data),
    }


def _forecast_item(
    item: dict[str, Any],
    timezone_offset: int,
) -> dict[str, Any]:
    main = item.get("main")

    if not isinstance(main, dict) or "temp" not in main or "dt" not in item:
        raise WeatherAPIError("Forecast data is incomplete.")

    timestamp = int(item["dt"])

    return {
        "timestamp": timestamp,
        "local_time": local_datetime(timestamp, timezone_offset),
        "temperature": float(main["temp"]),
        "temp_min": float(main.get("temp_min", main["temp"])),
        "temp_max": float(main.get("temp_max", main["temp"])),
        "pop": float(item.get("pop", 0)) * 100,
        "condition": _weather_condition(item),
    }


def _unavailable_hour(slot_hour: int) -> dict[str, Any]:
    return {
        "slot_hour": slot_hour,
        "available": False,
        "temperature": None,
        "pop": None,
        "condition": {
            "main": "Unknown",
            "description": "Unavailable",
            "icon": "",
        },
    }


def today_hourly_forecast(
    forecast_list: list[dict[str, Any]],
    timezone_offset: int,
) -> list[dict[str, Any]]:
    """
    Return the next eight real forecast points (the next 24 hours).

    OpenWeather provides forecasts only from the current time onward.  Using
    fixed midnight-based slots left the earlier cards blank after a search
    later in the day, so the UI now displays a continuous, truthful sequence.
    """
    parsed = [
        _forecast_item(item, timezone_offset)
        for item in forecast_list
    ]

    city_now = now_in_city(timezone_offset)
    upcoming = [item for item in parsed if item["local_time"] >= city_now]
    cards = upcoming[: len(TARGET_HOURS)]

    return [
        {
            **item,
            "slot_hour": item["local_time"].hour,
            "available": True,
        }
        for item in cards
    ]


def five_day_forecast(
    forecast_list: list[dict[str, Any]],
    timezone_offset: int,
) -> list[dict[str, Any]]:
    parsed = [
        _forecast_item(item, timezone_offset)
        for item in forecast_list
    ]

    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)

    for item in parsed:
        grouped[item["local_time"].date()].append(item)

    days: list[dict[str, Any]] = []

    for date_value in sorted(grouped)[:5]:
        entries = grouped[date_value]

        descriptions = Counter(
            entry["condition"]["description"]
            for entry in entries
        )

        representative_description = descriptions.most_common(1)[0][0]

        representative = next(
            entry
            for entry in entries
            if entry["condition"]["description"] == representative_description
        )

        days.append(
            {
                "date": date_value,
                "day_name": date_value.strftime("%a"),
                "temp_min": min(entry["temp_min"] for entry in entries),
                "temp_max": max(entry["temp_max"] for entry in entries),
                "condition": representative["condition"],
            }
        )

    return days


def get_dashboard_weather(city: str) -> dict[str, Any]:
    city = city.strip()

    if not city:
        raise WeatherAPIError("Enter a city name before searching.")

    current = process_current(get_current_weather(city))
    forecast_response = get_forecast(city)

    forecast_list = forecast_response.get("list")

    if not isinstance(forecast_list, list) or not forecast_list:
        raise WeatherAPIError("The forecast response did not contain usable data.")

    timezone_offset = current["timezone_offset"]

    hourly = today_hourly_forecast(
        forecast_list,
        timezone_offset,
    )

    daily = five_day_forecast(
        forecast_list,
        timezone_offset,
    )

    if not daily:
        raise WeatherAPIError("No usable 5-day forecast was available.")

    available_hourly = [
        item
        for item in hourly
        if item["available"]
    ]

    if available_hourly:
        city_now = now_in_city(timezone_offset)

        closest_forecast = min(
            available_hourly,
            key=lambda item: abs(
                (item["local_time"] - city_now).total_seconds()
            ),
        )

        current["rain_chance"] = closest_forecast["pop"]
    else:
        current["rain_chance"] = None

    return {
        "current": current,
        "hourly": hourly,
        "daily": daily,
    }
