from types import SimpleNamespace

from app.agents.route_agent import RouteAgent
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
