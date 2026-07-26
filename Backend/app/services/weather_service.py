from datetime import date, datetime, timedelta, timezone

from app.core.config import settings
from app.services.google_maps import google_maps_service
from app.services.map_http import map_http_client


class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"

    def _daily_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[date, dict]:
        if google_maps_service.enabled("weather"):
            try:
                google_forecast = google_maps_service.daily_weather(latitude, longitude)
                if google_forecast:
                    return google_forecast
            except Exception:
                pass

        if not settings.OPENWEATHER_API_KEY:
            return {}

        cache_key = f"forecast:{latitude:.4f}:{longitude:.4f}"
        data = map_http_client.get_json(
            self.BASE_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "appid": settings.OPENWEATHER_API_KEY,
                "units": "metric",
            },
            timeout=15,
            cache_key=cache_key,
            context="OpenWeather forecast",
        )

        timezone_offset = (data.get("city") or {}).get("timezone", 0)
        daily_forecast: dict[date, dict] = {}

        for forecast_item in data.get("list", []):
            timestamp = forecast_item.get("dt")

            if not timestamp:
                continue

            forecast_date = (
                datetime.fromtimestamp(timestamp, tz=timezone.utc)
                + timedelta(seconds=timezone_offset)
            ).date()

            main_data = forecast_item.get("main") or {}
            weather_items = forecast_item.get("weather") or []
            primary_weather = weather_items[0] if weather_items else {}
            rain_data = forecast_item.get("rain") or {}

            summary = daily_forecast.setdefault(
                forecast_date,
                {
                    "temp_min": None,
                    "temp_max": None,
                    "max_precipitation_probability": 0.0,
                    "rain_mm": 0.0,
                    "conditions": set(),
                },
            )

            temp_min = main_data.get("temp_min")
            temp_max = main_data.get("temp_max")

            if temp_min is not None:
                summary["temp_min"] = temp_min if summary["temp_min"] is None else min(summary["temp_min"], temp_min)

            if temp_max is not None:
                summary["temp_max"] = temp_max if summary["temp_max"] is None else max(summary["temp_max"], temp_max)

            summary["max_precipitation_probability"] = max(
                summary["max_precipitation_probability"],
                float(forecast_item.get("pop") or 0.0),
            )
            summary["rain_mm"] += float(rain_data.get("3h") or 0.0)

            if primary_weather.get("main"):
                summary["conditions"].add(primary_weather["main"])

        return daily_forecast

    def summarize_place_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        category: str,
    ) -> tuple[str | None, list[str]]:
        today = datetime.now(timezone.utc).date()
        if end_date < today or start_date > today + timedelta(days=9):
            return None, []

        daily_forecast = self._daily_forecast(latitude, longitude)

        if not daily_forecast:
            return None, []

        outdoor_categories = {
            "nature",
            "adventure",
            "viewpoint",
            "beach",
            "historical",
            "religious",
        }

        trip_dates = []
        current_date = start_date

        while current_date <= end_date:
            trip_dates.append(current_date)
            current_date += timedelta(days=1)

        relevant_days = [
            daily_forecast[trip_date]
            for trip_date in trip_dates
            if trip_date in daily_forecast
        ]

        if not relevant_days:
            return None, []

        maximums = [day["temp_max"] for day in relevant_days if day["temp_max"] is not None]
        minimums = [day["temp_min"] for day in relevant_days if day["temp_min"] is not None]
        if not maximums or not minimums:
            return None, []

        max_temp = max(maximums)
        min_temp = min(minimums)
        max_precipitation_probability = max(
            day["max_precipitation_probability"] for day in relevant_days
        )
        rainiest_total_mm = max(day["rain_mm"] for day in relevant_days)
        conditions = sorted(
            {
                condition
                for day in relevant_days
                for condition in day["conditions"]
            }
        )

        summary_parts = []

        if conditions:
            summary_parts.append(f"Conditions: {', '.join(conditions[:3])}")

        summary_parts.append(f"Temp: {round(min_temp)}C to {round(max_temp)}C")

        if max_precipitation_probability >= 0.2 or rainiest_total_mm > 0:
            summary_parts.append(
                f"Rain chance up to {round(max_precipitation_probability * 100)}%"
            )

        warnings = []

        if "Thunderstorm" in conditions:
            warnings.append(
                "Weather consideration: thunderstorms are forecast during the trip. Keep this stop flexible."
            )

        if max_precipitation_probability >= 0.55 or rainiest_total_mm >= 6:
            warnings.append(
                "Weather consideration: rain is likely during the trip dates for this place."
            )

        if category in outdoor_categories and max_temp >= 32:
            warnings.append(
                "Weather consideration: hot daytime weather is expected. Prefer morning or sunset visits for outdoor comfort."
            )

        if category == "beach" and max_precipitation_probability >= 0.4:
            warnings.append(
                "Weather consideration: beach conditions may be less favorable because of rain risk."
            )

        return "; ".join(summary_parts), warnings
