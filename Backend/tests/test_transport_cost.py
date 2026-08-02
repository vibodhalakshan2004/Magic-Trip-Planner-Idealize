from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.agents.budget_agent import BudgetAgent
from app.schemas.budget import BudgetCalculateRequest
from app.services.google_maps import google_maps_service
from app.services.transport_cost import (
    estimate_normal_bus_fare_per_person,
    estimate_saved_route_transport_cost,
    estimate_segment_transport_cost_details,
)


def _disable_live_fares(monkeypatch):
    monkeypatch.setattr(google_maps_service, "transit_fare", lambda **_kwargs: None)


def _path():
    return [
        {"latitude": 6.9271, "longitude": 79.8612},
        {"latitude": 7.2906, "longitude": 80.6337},
    ]


def test_bus_uses_ntc_fare_per_person_instead_of_flat_per_kilometre(monkeypatch):
    _disable_live_fares(monkeypatch)

    estimate = estimate_segment_transport_cost_details(
        transport_type="bus",
        distance_km=250,
        travelers=2,
        origin={"latitude": 6.9271, "longitude": 79.8612},
        destination={"latitude": 7.2906, "longitude": 80.6337},
    )

    assert estimate.per_person_lkr == estimate_normal_bus_fare_per_person(250)
    assert estimate.total_lkr == estimate.per_person_lkr * 2
    assert estimate.total_lkr < 3000
    assert "NTC" in estimate.source


def test_live_bus_fare_is_multiplied_only_by_passenger_count(monkeypatch):
    monkeypatch.setattr(
        google_maps_service,
        "transit_fare",
        lambda **_kwargs: {"fare_lkr": 275, "provider": "test"},
    )

    estimate = estimate_segment_transport_cost_details(
        transport_type="bus",
        distance_km=40,
        travelers=3,
        origin={"latitude": 6.9, "longitude": 79.8},
        destination={"latitude": 7.0, "longitude": 80.0},
    )

    assert estimate.total_lkr == 825
    assert estimate.per_person_lkr == 275
    assert estimate.passenger_count == 3
    assert estimate.fare_is_live is True


def test_mixed_mode_uses_group_vehicle_locally_and_bus_for_long_legs(monkeypatch):
    _disable_live_fares(monkeypatch)

    local_two_people = estimate_segment_transport_cost_details("mixed", 5, 2)
    local_four_people = estimate_segment_transport_cost_details("mixed", 5, 4)
    intercity = estimate_segment_transport_cost_details("mixed", 120, 4)

    assert local_two_people.total_lkr == local_four_people.total_lkr == 500
    assert local_two_people.per_person_lkr is None
    assert intercity.per_person_lkr is not None
    assert intercity.total_lkr == intercity.per_person_lkr * 4


def test_saved_route_reprices_legacy_segment_costs(monkeypatch):
    _disable_live_fares(monkeypatch)
    route = SimpleNamespace(
        days=[
            {
                "segments": [
                    {
                        "from_name": "Colombo",
                        "to_name": "Kandy",
                        "distance_km": 120,
                        "transport_cost_lkr": 99999,
                        "path_coordinates": _path(),
                    }
                ]
            }
        ]
    )

    estimate = estimate_saved_route_transport_cost(route, "bus", 2)

    assert estimate is not None
    assert estimate.total_lkr == estimate_normal_bus_fare_per_person(120) * 2
    assert estimate.total_lkr < 2000


def test_budget_does_not_add_hotel_transfer_already_in_saved_route(monkeypatch):
    _disable_live_fares(monkeypatch)
    trip = SimpleNamespace(
        id=uuid4(),
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        travelers=2,
        transport_type="bus",
        budget_min=1000,
        budget_max=100000,
        destination="Kandy",
    )
    hotel = SimpleNamespace(
        name="Kandy Guest House",
        transfer_cost_lkr=500,
        total_estimated_price_lkr=0,
    )
    route = SimpleNamespace(
        total_distance_km=10,
        total_transport_cost_lkr=99999,
        days=[
            {
                "segments": [
                    {
                        "from_name": "Temple",
                        "to_name": "Kandy Guest House",
                        "distance_km": 10,
                        "path_coordinates": _path(),
                    }
                ]
            }
        ],
    )

    result = BudgetAgent().calculate_budget(
        trip=trip,
        selected_places=[SimpleNamespace(estimated_cost_lkr_per_person=0)],
        selected_hotels=[hotel],
        request=BudgetCalculateRequest(
            food_cost_per_person_per_day_lkr=0,
            shopping_other_cost_lkr=0,
        ),
        route_plan=route,
    )

    expected = estimate_normal_bus_fare_per_person(10) * 2
    assert result.transport_cost_lkr == expected


def test_budget_adds_only_hotel_transfer_missing_from_route(monkeypatch):
    _disable_live_fares(monkeypatch)
    trip = SimpleNamespace(
        id=uuid4(),
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        travelers=2,
        transport_type="bus",
        budget_min=1000,
        budget_max=100000,
        destination="Kandy",
    )
    hotel = SimpleNamespace(
        name="Unrouted Hotel",
        transfer_cost_lkr=500,
        total_estimated_price_lkr=0,
    )
    route = SimpleNamespace(
        total_distance_km=10,
        days=[
            {
                "segments": [
                    {
                        "from_name": "Temple",
                        "to_name": "Market",
                        "distance_km": 10,
                        "path_coordinates": _path(),
                    }
                ]
            }
        ],
    )

    result = BudgetAgent().calculate_budget(
        trip=trip,
        selected_places=[SimpleNamespace(estimated_cost_lkr_per_person=0)],
        selected_hotels=[hotel],
        request=BudgetCalculateRequest(
            food_cost_per_person_per_day_lkr=0,
            shopping_other_cost_lkr=0,
        ),
        route_plan=route,
    )

    expected_route = estimate_normal_bus_fare_per_person(10) * 2
    assert result.transport_cost_lkr == expected_route + 500
