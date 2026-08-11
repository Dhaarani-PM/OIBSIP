from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import config


def local_datetime(timestamp: int | float, timezone_offset: int) -> datetime:
    city_timezone = timezone(timedelta(seconds=timezone_offset))
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(city_timezone)


def now_in_city(timezone_offset: int) -> datetime:
    city_timezone = timezone(timedelta(seconds=timezone_offset))
    return datetime.now(timezone.utc).astimezone(city_timezone)


def celsius_to_fahrenheit(value: float) -> float:
    return value * 9 / 5 + 32


def format_number(value: float | int | None, decimals: int = 1) -> str:
    if value is None:
        return "—"

    value = float(value)

    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))

    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def format_temperature(celsius: float | None, unit: str = "C") -> str:
    if celsius is None:
        return "—"

    value = celsius_to_fahrenheit(celsius) if unit == "F" else celsius
    suffix = "°F" if unit == "F" else "°C"
    return f"{format_number(value)}{suffix}"


def format_wind_speed(speed_mps: float | None) -> str:
    if speed_mps is None:
        return "—"

    return f"{format_number(speed_mps * 3.6)} km/h"


def safe_path(path: Path) -> Path | None:
    return path if path.exists() else None


def weather_icon_path(condition: dict[str, Any]) -> Path | None:
    """
    Maps OpenWeather conditions to the user's existing local assets only.
    No generated, downloaded, emoji, or Unicode weather icons are used.
    """
    main = str(condition.get("main", "")).lower()
    condition_id = int(condition.get("id", 0))
    icon_code = str(condition.get("icon", ""))
    is_night = icon_code.endswith("n")

    if main == "clear":
        filename = "clear_night.png" if is_night else "clear_day.png"

    elif main == "clouds":
        if condition_id == 801:
            filename = (
                "partly_cloudy_night.png"
                if is_night
                else "partly_cloudy_day.png"
            )
        else:
            filename = "cloudy.png"

    elif main in {"rain", "drizzle"}:
        filename = "rainy.png"

    elif main == "snow":
        filename = "snowy.png"

    elif main == "thunderstorm":
        filename = "thunderstorm.png"

    else:
       
        fog_icon = safe_path(config.ICONS_DIR / "foggy.png")
        if main in {
            "mist", "smoke", "haze", "dust", "fog",
            "sand", "ash", "squall", "tornado",
        } and fog_icon:
            return fog_icon

        filename = "cloudy.png"

    return safe_path(config.ICONS_DIR / filename)


def background_path(current: dict[str, Any]) -> Path | None:
    """
    Uses the searched city's OpenWeather condition and icon state.
    Day/night never depends on the computer's local time.
    """
    condition = current.get("condition", {})
    main = str(condition.get("main", "")).lower()
    icon_code = str(condition.get("icon", ""))

    timestamp = int(current.get("timestamp", 0))
    sunrise = int(current.get("sunrise", 0))
    sunset = int(current.get("sunset", 0))

   
    is_night = icon_code.endswith("n")

    
    if not icon_code and sunrise and sunset:
        is_night = not (sunrise <= timestamp <= sunset)

   
    if is_night and main not in {
        "rain", "drizzle", "snow", "thunderstorm", "mist", "smoke",
        "haze", "dust", "fog", "sand", "ash", "squall", "tornado",
    }:
        filename = "night.jpg"
    elif main == "clear":
        filename = "sunny.jpeg"
    elif main == "clouds":
        filename = "cloudy.jpeg"
    elif main in {"rain", "drizzle"}:
        filename = "rainy.webp"
    elif main == "snow":
        filename = "snowy.jpg"
    elif main == "thunderstorm":
        filename = "stormy.jpg"
    elif main in {
        "mist", "smoke", "haze", "dust", "fog",
        "sand", "ash", "squall", "tornado",
    }:
        filename = "foggy.jpg"
    else:
        filename = "cloudy.jpeg"
        

    return safe_path(config.BACKGROUNDS_DIR / filename)


def shortened_description(text: str, limit: int = 13) -> str:
    text = text.title()
    return text if len(text) <= limit else f"{text[:limit - 1]}…"
