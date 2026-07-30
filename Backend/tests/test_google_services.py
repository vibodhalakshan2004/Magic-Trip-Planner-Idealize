from datetime import date

import pytest

from app.core.config import settings
from app.services.google_maps import GoogleMapsService
from app.services.google_quota import GoogleQuotaExceeded, GoogleQuotaGuard
from app.services.map_http import MapHttpClient, map_http_client


def test_google_quota_guard_stops_before_configured_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_WEATHER_MONTHLY_LIMIT", 2)
    guard = GoogleQuotaGuard(tmp_path / "usage.sqlite3")

    assert guard.reserve("weather").remaining == 1
    assert guard.reserve("weather").remaining == 0

    with pytest.raises(GoogleQuotaExceeded):
        guard.reserve("weather")


def test_provider_response_cache_prevents_duplicate_http_calls(monkeypatch):
    client = MapHttpClient()
    calls = []
    monkeypatch.setattr(settings, "PROVIDER_CACHE_ENABLED", False)

    class Response:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"items": ["cached"]}

    def fake_get(*args, **kwargs):
        calls.append(args[0])
        return Response()

    monkeypatch.setattr(client._session, "get", fake_get)
    first = client.get_json("https://example.invalid/data", cache_key="test-cache")
    second = client.get_json("https://example.invalid/data", cache_key="test-cache")

    assert first == second == {"items": ["cached"]}
    assert calls == ["https://example.invalid/data"]


def test_google_daily_weather_parser_uses_one_guarded_request(monkeypatch):
    service = GoogleMapsService()
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-only-key")
    monkeypatch.setattr(settings, "GOOGLE_WEATHER_ENABLED", True)
    calls = []

    def fake_get_json(*args, **kwargs):
        calls.append(kwargs["params"])
        return {
            "forecastDays": [
                {
                    "displayDate": {"year": 2026, "month": 7, "day": 22},
                    "daytimeForecast": {
                        "weatherCondition": {"description": {"text": "Rain showers"}},
                        "precipitation": {"probability": {"percent": 70}, "qpf": {"quantity": 8}},
                        "thunderstormProbability": 40,
                    },
                    "nighttimeForecast": {
                        "weatherCondition": {"description": {"text": "Cloudy"}},
                        "precipitation": {"probability": {"percent": 30}, "qpf": {"quantity": 1}},
                    },
                    "maxTemperature": {"degrees": 31},
                    "minTemperature": {"degrees": 24},
                }
            ]
        }

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)
    forecast = service.daily_weather(6.9271, 79.8612)

    assert len(calls) == 1
    assert calls[0]["location.latitude"] == 6.93
    assert forecast[date(2026, 7, 22)]["rain_mm"] == 9
    assert forecast[date(2026, 7, 22)]["max_precipitation_probability"] == 0.7
    assert "Thunderstorm" in forecast[date(2026, 7, 22)]["conditions"]


def test_google_route_parser_returns_existing_route_contract(monkeypatch):
    service = GoogleMapsService()
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-only-key")
    monkeypatch.setattr(settings, "GOOGLE_ROUTES_ENABLED", True)

    monkeypatch.setattr(
        map_http_client,
        "post_json",
        lambda *args, **kwargs: {
            "routes": [
                {
                    "distanceMeters": 12500,
                    "duration": "1800s",
                    "polyline": {"encodedPolyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@"},
                    "legs": [
                        {
                            "steps": [
                                {
                                    "distanceMeters": 1000,
                                    "staticDuration": "120s",
                                    "navigationInstruction": {"instructions": "Head east"},
                                }
                            ]
                        }
                    ],
                }
            ]
        },
    )

    result = service.route_between(
        {"latitude": 6.9, "longitude": 79.8},
        {"latitude": 6.8, "longitude": 80.0},
        "car",
    )

    assert result is not None
    assert result["distance_km"] == 12.5
    assert result["duration_minutes"] == 30
    assert result["instructions"][0]["instruction"] == "Head east"
    assert result["path_coordinates"]
