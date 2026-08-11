from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageTk

import config
from api import WeatherAPIError
from utils import (
    background_path,
    format_number,
    format_temperature,
    format_wind_speed,
    now_in_city,
    shortened_description,
    weather_icon_path,
)
from weather import TARGET_HOURS, get_dashboard_weather


class WeatherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced Weather Dashboard")
        self.root.geometry("1200x720")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#71807b")

        self.canvas = tk.Canvas(root, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.render())

        self.search_var = tk.StringVar()

        self.search_entry = tk.Entry(
            root,
            textvariable=self.search_var,
            font=("Georgia", 12),
            fg="#ffffff",
           
            bg="#78979b",
            insertbackground="#ffffff",
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.search_entry.bind("<Return>", lambda _event: self.search())
        self.search_entry.bind("<FocusIn>", self._clear_error)

        self.search_button = self._make_button("Get Weather", self.search)
        self.c_button = self._make_button("°C", lambda: self.set_unit("C"))
        self.f_button = self._make_button("°F", lambda: self.set_unit("F"))

        self.unit = "C"
        self.dashboard: dict[str, Any] | None = None
        self.error_message = ""
        self.loading = False

        self.background_image: Image.Image | None = None
        self.background_photo: ImageTk.PhotoImage | None = None
        self.glass_photos: list[ImageTk.PhotoImage] = []
        self.icon_photos: list[ImageTk.PhotoImage] = []

        self.hour_scroll = 0.0
        self._scroll_target = 0.0
        self._scroll_animation_running = False
        self.pending_hour_index: int | None = None
        self.forecast_geometry: dict[str, float] = {}

        self.root.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Shift-MouseWheel>", self._on_horizontal_wheel)

        self.render()

    def _make_button(self, text: str, command: Any) -> tk.Button:
        return tk.Button(
            self.root,
            text=text,
            command=command,
            font=("Georgia", 11),
            fg="#ffffff",
            bg="#78979b",
            activeforeground="#ffffff",
            activebackground="#9db6b8",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=3,
            highlightthickness=0,
        )

    def _on_resize(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self.render()

    def _clear_error(self, _event: tk.Event | None = None) -> None:
        if self.error_message:
            self.error_message = ""
            self.render()

    def search(self) -> None:
        city = self.search_var.get().strip()

        if not city:
            self.error_message = "Enter a city name before searching."
            self.render()
            return

        if self.loading:
            return

        self.loading = True
        self.error_message = ""
        self.search_button.configure(text="Loading…", state="disabled")
        self.render()

        threading.Thread(
            target=self._load_weather,
            args=(city,),
            daemon=True,
        ).start()

    def _load_weather(self, city: str) -> None:
        try:
            weather_data = get_dashboard_weather(city)
            self.root.after(0, lambda: self._search_success(weather_data))
        except WeatherAPIError as exc:
            self.root.after(0, lambda: self._search_failed(str(exc)))
        except Exception:
            self.root.after(
                0,
                lambda: self._search_failed(
                    "Unable to load weather data. Please try again."
                ),
            )

    def _search_success(self, weather_data: dict[str, Any]) -> None:
        self.dashboard = weather_data
        self.loading = False
        self.error_message = ""
        self.search_button.configure(text="Get Weather", state="normal")
        self._scroll_to_current_hour()
        self.render()

    def _search_failed(self, message: str) -> None:
        self.loading = False
        self.error_message = message
        self.search_button.configure(text="Get Weather", state="normal")
        self.render()

    def set_unit(self, unit: str) -> None:
        self.unit = unit
        self.render()

    def _text(
        self,
        x: float,
        y: float,
        text: str,
        size: int,
        *,
        anchor: str = "nw",
        fill: str = "#ffffff",
        bold: bool = False,
        family: str = "Georgia",
    ) -> int:
        return self.canvas.create_text(
            x,
            y,
            text=text,
            anchor=anchor,
            fill=fill,
            font=(family, size, "bold" if bold else "normal"),
        )

    def _load_background(self, width: int, height: int) -> None:
        background: Path | None = None

        if self.dashboard:
            background = background_path(self.dashboard["current"])

        if background is None:
            background = config.BACKGROUNDS_DIR / "default_teal.png"

        try:
            image = Image.open(background).convert("RGB")
            image = ImageOps.fit(
                image,
                (width, height),
                method=Image.Resampling.LANCZOS,
            )
        except Exception:
            image = Image.new("RGB", (width, height), "#74827d")

        self.background_image = image
        self.background_photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.background_photo)

    def _glass_panel(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: int = 16,
        opacity: int = 55,
        blur: float = 1.4,
    ) -> None:
        """
        A panel is a lightly blurred crop of the weather image with a subtle
        white tint and border. No stipple/dotted/mesh texture is used.
        """
        if self.background_image is None:
            return

        x1 = int(max(0, x1))
        y1 = int(max(0, y1))
        x2 = int(min(self.background_image.width, x2))
        y2 = int(min(self.background_image.height, y2))

        if x2 <= x1 or y2 <= y1:
            return

        panel = self.background_image.crop((x1, y1, x2, y2)).convert("RGBA")

        if blur > 0:
            panel = panel.filter(ImageFilter.GaussianBlur(blur))

        white_tint = Image.new(
            "RGBA",
            panel.size,
            (244, 248, 246, opacity),
        )
        panel = Image.alpha_composite(panel, white_tint)

        mask = Image.new("L", panel.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            (0, 0, panel.width - 1, panel.height - 1),
            radius=radius,
            fill=225,
        )
        panel.putalpha(mask)

        panel_draw = ImageDraw.Draw(panel)
        panel_draw.rounded_rectangle(
            (0, 0, panel.width - 1, panel.height - 1),
            radius=radius,
            outline=(255, 255, 255, 125),
            width=1,
        )

        photo = ImageTk.PhotoImage(panel)
        self.glass_photos.append(photo)
        self.canvas.create_image(x1, y1, image=photo, anchor="nw")

    def _draw_icon(
        self,
        x: float,
        y: float,
        condition: dict[str, Any],
        size: int,
    ) -> None:
        icon_path = weather_icon_path(condition)

        if icon_path is None:
            return

        try:
            image = Image.open(icon_path).convert("RGBA")
            image.thumbnail((size, size), Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(image)
            self.icon_photos.append(photo)
            self.canvas.create_image(x, y, image=photo, anchor="center")
        except Exception:
            return

    def _draw_asset_icon(self, x: float, y: float, name: str, size: int) -> None:
        """Draw a bundled interface icon centred at the given position."""
        try:
            image = Image.open(config.ICONS_DIR / f"{name}.png").convert("RGBA")
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.icon_photos.append(photo)
            self.canvas.create_image(x, y, image=photo, anchor="center")
        except Exception:
            return

    def _place_search_controls(self, width: int) -> None:
        entry_left = 73
        entry_width = 220
        button_x = entry_left + entry_width + 12
        c_x = button_x + 120
        f_x = c_x + 50

        self.canvas.create_window(
            entry_left,
            33,
            anchor="w",
            window=self.search_entry,
            width=entry_width,
            height=27,
        )
        self.canvas.create_window(
            button_x,
            33,
            anchor="w",
            window=self.search_button,
            width=110,
            height=30,
        )
        self.canvas.create_window(
            c_x,
            33,
            anchor="w",
            window=self.c_button,
            width=42,
            height=30,
        )
        self.canvas.create_window(
            f_x,
            33,
            anchor="w",
            window=self.f_button,
            width=42,
            height=30,
        )

        active = "#9db6b8"
        inactive = "#78979b"
        self.c_button.configure(bg=active if self.unit == "C" else inactive)
        self.f_button.configure(bg=active if self.unit == "F" else inactive)

    def _draw_search_bar(self, width: int) -> None:
        bar_right = min(width - 30, 610)

        self._glass_panel(
            30,
            10,
            bar_right,
            57,
            radius=14,
            opacity=52,
            blur=1.0,
        )
        self._draw_asset_icon(51, 33, "search", 26)
        self._place_search_controls(width)

        if self.error_message:
            self._text(
                bar_right + 18,
                34,
                self.error_message,
                10,
                anchor="w",
                fill="#fff1f1",
                family="Segoe UI",
            )

    def _draw_empty_state(self, width: int, height: int) -> None:
        self._text(74, 155, "LIVE CITY WEATHER", 9, fill="#e2c98a")
        self._text(74, 188, "See the sky", 38)
        self._text(
            74,
            235,
            "where you",
            38,
            fill="#e2c98a",
            bold=True,
        )

        self._text(
            74,
            282,
            "are.",
            38,
            fill="#e2c98a",
            bold=True,
        )
        self._text(
            75,
            350,
            "Search for a city to load live weather and\nforecast data.",
            12,
            fill="#d8e0df",
        )

       
        panel_top = height + 10
        panel_bottom = min(height - 50, 405)

        self._glass_panel(
            52,
            panel_top,
            width - 52,
            panel_bottom,
            radius=18,
            opacity=45,
        )

        self._text(
            width / 2,
            panel_top + 55,
            "The weather photograph remains the focus.",
            17,
            anchor="center",
        )
        self._text(
            width / 2,
            panel_top + 91,
            "Live conditions  ·  Hourly forecast  ·  5-day outlook",
            12,
            anchor="center",
            fill="#edf4f1",
        )

    def _draw_current_weather(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
    ) -> None:
        current = self.dashboard["current"]
        location = current["city"]

        if current["country"]:
            location = f"{location}, {current['country']}"

        self._draw_asset_icon(left + 18, top + 24, "location", 20)
        self._text(left + 40, top + 10, location, 18, bold=True)

        temperature_x = left + 68
        temperature_y = top + 73

        self._text(
            temperature_x,
            temperature_y,
            format_temperature(current["temperature"], self.unit),
            46,
        )

        self.canvas.create_line(
            temperature_x,
            top + 134,
            temperature_x + 96,
            top + 134,
            fill="#72d2ef",
            width=3,
        )

        chance = current.get("rain_chance")
        chance_text = (
            f"Chance of rain {format_number(chance)}%"
            if chance is not None
            else "Chance of rain unavailable"
        )
        self._text(temperature_x, top + 153, chance_text, 13, fill="#edf5f2")

    def _draw_today_forecast(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        self._glass_panel(x1, y1, x2, y2, radius=15, opacity=52)
        self._text(x1 + 16, y1 + 10, "Next 24 Hours", 14, bold=True)

        inner_left = x1 + 18
        inner_right = x2 - 18
        cards_top = y1 + 39
        
        cards_bottom = y2 - 27

        viewport_width = inner_right - inner_left
        gap = 10
        card_width = (viewport_width - gap * 3) / 4

        card_count = max(len(self.dashboard["hourly"]), 1)
        content_width = card_width * card_count + gap * (card_count - 1)
        max_scroll = max(0.0, content_width - viewport_width)

        if self.pending_hour_index is not None:
            target = self.pending_hour_index * (card_width + gap)

            self.hour_scroll = min(max(target, 0.0), max_scroll)
            self._scroll_target = self.hour_scroll
            self.pending_hour_index = None

        self.hour_scroll = min(max(self.hour_scroll, 0.0), max_scroll)

        self.forecast_geometry = {
            "panel_left": x1,
            "panel_right": x2,
            "inner_left": inner_left,
            "inner_right": inner_right,
            "cards_top": cards_top,
            "cards_bottom": cards_bottom,
            "scrollbar_y": y2 - 11,
            "max_scroll": max_scroll,
            "card_step": card_width + gap,
        }

        for index, item in enumerate(self.dashboard["hourly"]):
            card_x = inner_left + index * (card_width + gap) - self.hour_scroll
            card_right = card_x + card_width

          
            if card_x < inner_left - 0.5 or card_right > inner_right + 0.5:
                continue

            self._glass_panel(
                card_x,
                cards_top,
                card_right,
                cards_bottom,
                radius=12,
                opacity=62,
                blur=1.1,
            )

            center_x = card_x + card_width / 2

            self._text(
                center_x,
                cards_top + 12,
                f"{item['slot_hour']:02d}:00",
                10,
                anchor="n",
                fill="#f8fbfa",
            )

            self._draw_icon(center_x, cards_top + 42, item["condition"], 26)

            temperature = (
                format_temperature(item["temperature"], self.unit)
                if item["available"]
                else "—"
            )
            status = (
                shortened_description(item["condition"]["description"], 14)
                if item["available"]
                else "No data"
            )

            self._text(
                center_x,
                cards_top + 62,
                temperature,
                14,
                anchor="n",
                bold=True,
            )
            self._text(
                center_x,
                cards_top + 82,
                status,
                9,
                anchor="n",
                fill="#edf4f1",
            )
        track_y = y2 - 11

        self.canvas.create_line(
            inner_left,
            track_y,
            inner_right,
            track_y,
            fill="#edf4f1",
            width=2,
        )

        thumb_width = max(42, viewport_width / content_width * viewport_width)
        available_track = viewport_width - thumb_width
        thumb_x = inner_left

        if max_scroll > 0:
            thumb_x += (self.hour_scroll / max_scroll) * available_track

        self.canvas.create_line(
            thumb_x,
            track_y,
            thumb_x + thumb_width,
            track_y,
            fill="#ffffff",
            width=4,
        )

        self._text(x1 + 5, y2 - 17, "‹", 17, anchor="w")
        self._text(x2 - 5, y2 - 17, "›", 17, anchor="e")

    def _draw_air_conditions(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        self._glass_panel(x1, y1, x2, y2, radius=15, opacity=52)
        self._text(x1 + 16, y1 + 10, "Air Conditions", 14, bold=True)

        current = self.dashboard["current"]

        metrics = [
            ("♨", "Feels Like", format_temperature(current["feels_like"], self.unit)),
            (
                "♧",
                "Humidity",
                f"{format_number(current['humidity'])}%"
                if current["humidity"] is not None
                else "—",
            ),
            ("⌁", "Wind Speed", format_wind_speed(current["wind_speed"])),
            (
                "◌",
                "Pressure",
                f"{format_number(current['pressure'])} hPa"
                if current["pressure"] is not None
                else "—",
            ),
        ]
        metric_icons = ("feels_like", "humidity", "wind", "pressure")

        content_top = y1 + 42
        content_bottom = y2 - 11
        midpoint_x = (x1 + x2) / 2
        row_height = (content_bottom - content_top) / 2

        self.canvas.create_line(
            midpoint_x,
            content_top,
            midpoint_x,
            content_bottom,
            fill="#ffffff",
            width=1,
        )
        self.canvas.create_line(
            x1 + 14,
            content_top + row_height,
            x2 - 14,
            content_top + row_height,
            fill="#ffffff",
            width=1,
        )

        for index, (symbol, label, value) in enumerate(metrics):
            column = index % 2
            row = index // 2

            item_x = x1 + 20 if column == 0 else midpoint_x + 20
            item_y = content_top + row * row_height + 12

            self._draw_asset_icon(item_x + 8, item_y + 8, metric_icons[index], 17)
            self._text(item_x + 20, item_y, label, 11, fill="#e7efec")
            self._text(item_x + 20, item_y + 24, value, 14, bold=True)

    def _draw_five_day_forecast(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> None:
        self._glass_panel(x1, y1, x2, y2, radius=18, opacity=54, blur=1.7)
        self._text(x1 + 17, y1 + 15, "5-Day Forecast", 16, bold=True)

        timezone_offset = self.dashboard["current"]["timezone_offset"]
        current_city_date = now_in_city(timezone_offset).date()

        rows_top = y1 + 58
        row_height = (y2 - rows_top - 12) / 5

        for index, day in enumerate(self.dashboard["daily"][:5]):
            row_y = rows_top + index * row_height
            is_today = day["date"] == current_city_date

            if is_today:
                self._glass_panel(
                    x1 + 11,
                    row_y - 5,
                    x2 - 11,
                    row_y + row_height - 9,
                    radius=11,
                    opacity=78,
                    blur=1.0,
                )

            if index and not is_today:
                self.canvas.create_line(
                    x1 + 16,
                    row_y - 8,
                    x2 - 16,
                    row_y - 8,
                    fill="#ffffff",
                    width=1,
                )

            day_label = "Today" if is_today else day["day_name"]

            self._text(
                x1 + 18,
                row_y + 5,
                day_label,
                13,
                bold=is_today,
            )

            self._draw_icon(
                x1 + 76,
                row_y + row_height / 2 - 4,
                day["condition"],
                33,
            )

            self._text(
                x1 + 105,
                row_y + 6,
                shortened_description(day["condition"]["description"], 16),
                10,
                fill="#f2f6f4",
                bold=is_today,
            )

            self._text(
                x2 - 17,
                row_y + 31,
                f"{format_temperature(day['temp_min'], self.unit)} / "
                f"{format_temperature(day['temp_max'], self.unit)}",
                12,
                anchor="ne",
                bold=True,
            )

    def _scroll_to_current_hour(self) -> None:
        if not self.dashboard:
            return

        
        self.pending_hour_index = 0

    def _scroll_forecast_to(self, target: float) -> None:
        geometry = self.forecast_geometry

        if not geometry:
            return

        step = geometry["card_step"]
        clamped_target = min(max(target, 0.0), geometry["max_scroll"])
        self._scroll_target = min(
            round(clamped_target / step) * step,
            geometry["max_scroll"],
        )

       
        self.hour_scroll = self._scroll_target
        self._scroll_animation_running = False
        self.render()

    def _animate_forecast_scroll(self) -> None:
        difference = self._scroll_target - self.hour_scroll

        if abs(difference) < 1:
            self.hour_scroll = self._scroll_target
            self._scroll_animation_running = False
            self.render()
            return

        self.hour_scroll += difference * 0.28
        self.render()
        self.root.after(16, self._animate_forecast_scroll)

    def _scroll_forecast_page(self, forward: bool) -> None:
        geometry = self.forecast_geometry

        if not geometry:
            return

        step = geometry["card_step"] * 2
        direction = 1 if forward else -1
        self._scroll_forecast_to(self.hour_scroll + direction * step)

    def _on_horizontal_wheel(self, event: tk.Event) -> None:
        geometry = self.forecast_geometry

        if not geometry:
            return

        if geometry["cards_top"] <= event.y <= geometry["cards_bottom"]:
            step = geometry["card_step"] * 0.9
            target = self.hour_scroll + (-step if event.delta > 0 else step)
            self._scroll_forecast_to(target)

    def _on_canvas_click(self, event: tk.Event) -> None:
        geometry = self.forecast_geometry

        if not geometry:
            return

        inside_panel = (
            geometry["panel_left"] <= event.x <= geometry["panel_right"]
            and geometry["cards_top"] <= event.y <= geometry["cards_bottom"] + 20
        )

        if not inside_panel:
            return

        if event.x < geometry["panel_left"] + 34:
            self._scroll_forecast_page(forward=False)
            return

        if event.x > geometry["panel_right"] - 34:
            self._scroll_forecast_page(forward=True)
            return

        if abs(event.y - geometry["scrollbar_y"]) < 12:
            viewport = geometry["inner_right"] - geometry["inner_left"]
            fraction = (event.x - geometry["inner_left"]) / viewport
            self._scroll_forecast_to(fraction * geometry["max_scroll"])

    def render(self) -> None:
        width = max(self.canvas.winfo_width(), 1000)
        height = max(self.canvas.winfo_height(), 650)

        self.canvas.delete("all")
        self.glass_photos.clear()
        self.icon_photos.clear()

        self._load_background(width, height)
        self._draw_search_bar(width)

        if not self.dashboard:
            self._draw_empty_state(width, height)
            return

        margin = 30
        right_panel_left = int(width * 0.705)
        gap = 18

        left_x1 = margin
        left_x2 = right_panel_left - gap
        right_x1 = right_panel_left
        right_x2 = width - margin

        top = 80
        forecast_top = max(258, int(height * 0.42))
        forecast_bottom = forecast_top + 174
        air_top = forecast_bottom + 12
        air_bottom = height - 22

        self._draw_current_weather(
            left_x1,
            top,
            left_x2,
            forecast_top - 8,
        )

        self._draw_today_forecast(
            left_x1,
            forecast_top,
            left_x2,
            forecast_bottom,
        )

        self._draw_air_conditions(
            left_x1,
            air_top,
            left_x2,
            air_bottom,
        )

        self._draw_five_day_forecast(
            right_x1,
            top,
            right_x2,
            height - 22,
        )

        if self.loading:
            self._text(
                width / 2,
                70,
                "Loading weather…",
                10,
                anchor="center",
            )
