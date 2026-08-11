from typing import Any

import requests

import config


class WeatherAPIError(Exception):
    """Raised for displayable OpenWeatherMap/API errors."""


def _request(url: str, city: str) -> dict[str, Any]:
    if not config.API_KEY or config.API_KEY == "YOUR_API_KEY_HERE":
        raise WeatherAPIError("Add your OpenWeatherMap API key in config.py first.")

    try:
        response = requests.get(
            url,
            params={
                "q": city,
                "appid": config.API_KEY,
                "units": "metric",
            },
            timeout=config.REQUEST_TIMEOUT,
        )
    except requests.Timeout as exc:
        raise WeatherAPIError("The weather request timed out. Please try again.") from exc
    except requests.ConnectionError as exc:
        raise WeatherAPIError(
            "No network connection. Check your internet and try again."
        ) from exc
    except requests.RequestException as exc:
        raise WeatherAPIError(
            "Unable to contact OpenWeatherMap. Please try again."
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise WeatherAPIError("OpenWeatherMap returned an invalid response.") from exc

    if response.status_code == 401:
        raise WeatherAPIError("Your OpenWeatherMap API key is invalid.")

    if response.status_code == 404:
        raise WeatherAPIError("City not found. Check the spelling and try again.")

    if response.status_code >= 400:
        message = "Unknown API error"
        if isinstance(data, dict):
            api_message = data.get("message")
            if isinstance(api_message, str) and api_message.strip():
                message = api_message
        raise WeatherAPIError(f"Weather service error: {message}")

    if not isinstance(data, dict):
        raise WeatherAPIError("The weather service returned malformed data.")

    return data


def get_current_weather(city: str) -> dict[str, Any]:
    return _request(config.CURRENT_WEATHER_URL, city)


def get_forecast(city: str) -> dict[str, Any]:
    return _request(config.FORECAST_URL, city)
