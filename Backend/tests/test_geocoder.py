from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.agents.route_agent import RouteAgent
from app.api.routes import destination as destination_routes
from app.schemas.selected_place import SelectPlacesRequest
from app.services.geocoder import GeocoderService
from app.services.google_maps import google_maps_service
from app.services.map_http import map_http_client


def test_local_catalog_resolves_failed_sigiriya_plan_without_http(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)

    def fail_http(*_args, **_kwargs):
        raise AssertionError("known Sri Lanka landmarks must not require an HTTP lookup")

    monkeypatch.setattr(map_http_client, "get_json", fail_http)
    service = GeocoderService()

    expected = {
        "Sigiriya Rock Fortress tickets": (7.9566634, 80.7599301),
        "Minneriya National Park safari cost": (8.0161446, 80.8501390),
        "Hiriwadunna Village Safari price": (8.0423226, 80.7564622),
        "Bahirawakanda Vihara Buddha Statue": (7.29553, 80.63094),
        "Udawatta Kele Sanctuary": (7.2936206, 80.6441322),
    }
    for query, coordinates in expected.items():
        result = service.geocode(query)
        assert result is not None
        assert (result["latitude"], result["longitude"]) == coordinates
        assert result["provider"] == "local_catalog"


def test_route_agent_recovers_all_places_from_failed_job_without_http(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)
    monkeypatch.setattr(
        map_http_client,
        "get_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("catalog-backed route should remain offline")
        ),
    )
    agent = RouteAgent()
    trip = SimpleNamespace(id="trip", destination="Sigiriya")
    places = [
        SimpleNamespace(
            place_key="sigiriya",
            name="Sigiriya Rock Fortress",
            category="historical",
            search_query="Sigiriya Rock Fortress tickets",
            latitude=None,
            longitude=None,
        ),
        SimpleNamespace(
            place_key="minneriya",
            name="Minneriya National Park Safari",
            category="adventure",
            search_query="Minneriya National Park safari cost",
            latitude=None,
            longitude=None,
        ),
        SimpleNamespace(
            place_key="hiriwadunna",
            name="Hiriwadunna Village Safari",
            category="culture",
            search_query="Hiriwadunna Village Safari price",
            latitude=None,
            longitude=None,
        ),
    ]

    assert all(agent._point_from_place(place, trip) for place in places)
    assert all(place.latitude is not None and place.longitude is not None for place in places)


def test_geocoder_cleans_intent_words_before_free_provider_lookup(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)
    calls = []

    def fake_get_json(*_args, **kwargs):
        calls.append(kwargs["params"]["q"])
        return [{"display_name": "Test Falls", "lat": "7.1", "lon": "80.2"}]

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)
    result = GeocoderService().geocode("Test Falls tickets and history")

    assert result is not None
    assert calls == ["Test Falls, Sri Lanka"]


def test_geocoder_normalizes_city_center_walk_for_sri_lanka(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)
    calls = []

    def fake_get_json(*_args, **kwargs):
        calls.append(kwargs["params"]["q"])
        return [{"display_name": "Kandy", "lat": "7.293", "lon": "80.635"}]

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)
    result = GeocoderService().geocode("Kandy City Center Walk, Kandy, Sri Lanka")

    assert result is not None
    assert calls == ["Kandy city centre, Kandy, Sri Lanka"]


def test_geocoder_progressively_broadens_any_place_name(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)
    calls = []

    def fake_get_json(*_args, **kwargs):
        query = kwargs["params"]["q"]
        calls.append(query)
        if query == "Emerald Ridge, Kandy, Sri Lanka":
            return [
                {
                    "display_name": "Emerald Ridge, Kandy, Sri Lanka",
                    "lat": "7.31",
                    "lon": "80.64",
                }
            ]
        return []

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)

    result = GeocoderService().geocode_place(
        name="Emerald Ridge Nature Sanctuary",
        destination="Kandy",
        search_query="Emerald Ridge Nature Sanctuary Sri Lanka",
    )

    assert result is not None
    assert result["provider"] == "openstreetmap"
    assert calls[-1] == "Emerald Ridge, Kandy, Sri Lanka"
    assert len(calls) <= GeocoderService.MAX_FREE_PROVIDER_ATTEMPTS


def test_geocoder_uses_secondary_open_map_index_when_nominatim_misses(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)

    def fake_get_json(url, *_args, **_kwargs):
        if url == GeocoderService.BASE_URL:
            return []
        return {
            "features": [
                {
                    "properties": {
                        "name": "Ambuluwawa Biodiversity Complex",
                        "country": "Sri Lanka",
                        "countrycode": "LK",
                    },
                    "geometry": {
                        "coordinates": [80.5404367, 7.1585138]
                    },
                }
            ]
        }

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)

    result = GeocoderService().geocode_place(
        name="Ambuluwawa Biodiversity Complex Tower",
        destination="Gampola",
    )

    assert result is not None
    assert result["provider"] == "photon_openstreetmap"
    assert result["latitude"] == 7.1585138


def test_secondary_provider_does_not_accept_an_unrelated_fuzzy_result(monkeypatch):
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: False)

    def fake_get_json(url, *_args, **_kwargs):
        if url == GeocoderService.BASE_URL:
            return []
        return {
            "features": [
                {
                    "properties": {
                        "name": "Kandy City Centre",
                        "country": "Sri Lanka",
                        "countrycode": "LK",
                    },
                    "geometry": {"coordinates": [80.635, 7.293]},
                }
            ]
        }

    monkeypatch.setattr(map_http_client, "get_json", fake_get_json)

    assert GeocoderService().geocode_place(
        name="Invented Rainbow Castle",
        destination="Kandy",
    ) is None


def test_coordinate_validation_rejects_missing_and_out_of_range_values():
    assert GeocoderService.valid_coordinate_pair(7.2, 80.6)
    assert not GeocoderService.valid_coordinate_pair(None, 80.6)
    assert not GeocoderService.valid_coordinate_pair(95, 80.6)


def test_unresolved_places_are_rejected_before_saved_selections_are_deleted(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    trip = SimpleNamespace(id=uuid4(), user_id=user.id, destination="Kandy")

    class Query:
        def filter(self, *_args):
            return self

        def first(self):
            return trip

        def delete(self):
            raise AssertionError("existing selections must remain untouched")

    db = SimpleNamespace(query=lambda _model: Query())
    monkeypatch.setattr(
        destination_routes.geocoder_service,
        "geocode_candidates",
        lambda *_args, **_kwargs: None,
    )

    request = SelectPlacesRequest(
        selected_places=[
            {
                "place_key": "invented_place",
                "name": "Invented Place",
                "category": "other",
                "source": "ai_suggested",
            }
        ]
    )

    with pytest.raises(HTTPException) as error:
        destination_routes.select_places_for_trip(
            trip.id, request, db, user
        )

    assert error.value.status_code == 422
    assert error.value.detail["unresolved_places"] == ["Invented Place"]


def test_geocoder_allows_only_one_google_attempt_per_logical_lookup(monkeypatch):
    google_calls = []
    free_calls = []
    monkeypatch.setattr(google_maps_service, "enabled", lambda _service: True)
    monkeypatch.setattr(
        google_maps_service,
        "geocode",
        lambda query, country: google_calls.append((query, country)),
    )
    monkeypatch.setattr(
        map_http_client,
        "get_json",
        lambda *_args, **kwargs: free_calls.append(kwargs["params"]["q"]) or [],
    )

    result = GeocoderService().geocode_candidates(
        ["Unknown Place tickets", "Unknown Place price", "Unknown Place"]
    )

    assert result is None
    assert len(google_calls) == 1
    assert len(free_calls) <= GeocoderService.MAX_FREE_PROVIDER_ATTEMPTS
