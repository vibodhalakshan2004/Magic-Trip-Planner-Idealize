from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agents.destination_agent import DestinationAgent
from app.api.routes.hotels import _haversine_distance_km
from app.services.google_maps import google_maps_service
from app.services.hotel_search import HotelSearchService
from app.services.map_http import map_http_client


def test_nearby_hotel_search_is_bounded_and_stops_after_results(monkeypatch):
    calls = []

    monkeypatch.setattr(google_maps_service, "enabled", lambda feature: False)

    def fake_get_json(url, **kwargs):
        calls.append((url, kwargs))
        return [
            {
                "osm_type": "node",
                "osm_id": 42,
                "display_name": "Test Hotel, Dambulla, Sri Lanka",
                "lat": "7.8742",
                "lon": "80.7718",
                "type": "hotel",
                "address": {"tourism": "Test Hotel", "town": "Dambulla"},
                "extratags": {
                    "description": "A quiet hotel near the route.",
                    "wikimedia_commons": "File:Test Hotel.jpg",
                },
            }
        ]

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)

    suggestions = HotelSearchService().search_hotels(
        query="hotel",
        destination="Dambulla",
        limit=8,
        latitude=7.8742,
        longitude=80.7718,
    )

    assert len(calls) == 1
    params = calls[0][1]["params"]
    assert params["bounded"] == 1
    assert params["countrycodes"] == "lk"
    assert params["viewbox"]
    assert suggestions[0]["name"] == "Test Hotel"
    assert suggestions[0]["image_url"].endswith("Test%20Hotel.jpg")


def test_google_hotel_search_requests_and_keeps_only_lodging(monkeypatch):
    captured = {}
    monkeypatch.setattr(google_maps_service, "enabled", lambda feature: feature == "places")

    def fake_search(query, limit, **kwargs):
        captured.update({"query": query, "limit": limit, **kwargs})
        return [
            {
                "id": "real-hotel",
                "displayName": {"text": "Verified Kandy Hotel"},
                "formattedAddress": "Kandy, Sri Lanka",
                "location": {"latitude": 7.29, "longitude": 80.63},
                "primaryType": "hotel",
                "types": ["hotel", "lodging"],
            },
            {
                "id": "not-a-hotel",
                "displayName": {"text": "Kandy Railway Station"},
                "formattedAddress": "Kandy, Sri Lanka",
                "location": {"latitude": 7.29, "longitude": 80.63},
                "primaryType": "train_station",
                "types": ["train_station", "transit_station"],
            },
        ]

    monkeypatch.setattr(google_maps_service, "search_places", fake_search)
    suggestions = HotelSearchService().search_hotels("hotel", "Kandy", limit=5)

    assert captured["included_type"] == "lodging"
    assert captured["strict_type_filtering"] is True
    assert [item["name"] for item in suggestions] == ["Verified Kandy Hotel"]


def test_osm_hotel_search_discards_non_accommodation_results(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda feature: False)
    monkeypatch.setattr(
        map_http_client,
        "get_json",
        lambda *args, **kwargs: [
            {
                "osm_type": "node",
                "osm_id": 1,
                "display_name": "Hotel Road, Kandy, Sri Lanka",
                "lat": "7.29",
                "lon": "80.63",
                "type": "residential",
                "class": "highway",
                "address": {"road": "Hotel Road", "city": "Kandy"},
            },
            {
                "osm_type": "node",
                "osm_id": 2,
                "display_name": "Real Guest House, Kandy, Sri Lanka",
                "lat": "7.30",
                "lon": "80.64",
                "type": "guest_house",
                "class": "tourism",
                "address": {"tourism": "Real Guest House", "city": "Kandy"},
            },
        ],
    )

    suggestions = HotelSearchService().search_hotels("hotel", "Kandy", limit=5)

    assert [item["name"] for item in suggestions] == ["Real Guest House"]


def test_osm_hotel_search_does_not_use_generic_hotel_as_the_name(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda feature: False)
    monkeypatch.setattr(
        map_http_client,
        "get_json",
        lambda *args, **kwargs: [
            {
                "osm_type": "node",
                "osm_id": 3,
                "display_name": "Devon Hotel, Kandy, Sri Lanka",
                "lat": "7.29",
                "lon": "80.63",
                "type": "hotel",
                "class": "tourism",
                "address": {"tourism": "Hotel", "city": "Kandy"},
            }
        ],
    )

    suggestions = HotelSearchService().search_hotels("hotel", "Kandy", limit=5)

    assert suggestions[0]["name"] == "Devon Hotel"


def test_place_media_lookup_still_runs_when_geocoding_fails(monkeypatch):
    trip = SimpleNamespace(
        id=uuid4(),
        destination="Sigiriya",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
    )
    agent = DestinationAgent()
    result = agent._mock_destination_response(trip)

    monkeypatch.setattr(
        agent.media_lookup,
        "lookup_media",
        lambda query: {"image_url": "https://upload.wikimedia.org/example.jpg", "description": None},
    )

    def fail_geocoding(query):
        raise TimeoutError("Nominatim unavailable")

    monkeypatch.setattr(agent.geocoder, "geocode", fail_geocoding)

    enriched = agent._enrich_with_weather(trip, result)

    assert all(place.image_url == "https://upload.wikimedia.org/example.jpg" for place in enriched.suggested_places)


def test_haversine_distance_is_local_and_predictable():
    assert _haversine_distance_km(7.0, 80.0, 7.0, 80.0) == 0
    assert _haversine_distance_km(7.0, 80.0, 8.0, 80.0) == pytest.approx(111.19, rel=0.01)
