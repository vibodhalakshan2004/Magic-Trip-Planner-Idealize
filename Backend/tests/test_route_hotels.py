from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.agents.route_agent import RouteAgent
from app.schemas.route import RoutePlanRequest


def test_hotel_waypoints_are_routed_on_empty_final_day_before_home():
    agent = RouteAgent()
    agent.geocoder = SimpleNamespace(
        geocode=lambda query: (
            {"latitude": 6.9271, "longitude": 79.8612}
            if "Colombo" in query
            else {"latitude": 6.8667, "longitude": 81.0466}
        )
    )

    def route_between(origin, destination, transport_type):
        return {
            "distance_km": 10,
            "duration_minutes": 20,
            "encoded_polyline": "test",
            "path_coordinates": [
                {"latitude": origin["latitude"], "longitude": origin["longitude"]},
                {"latitude": destination["latitude"], "longitude": destination["longitude"]},
            ],
            "instructions": [
                {"instruction": "Continue", "distance_km": 10, "duration_minutes": 20}
            ],
        }

    agent.router = SimpleNamespace(
        route_between=route_between,
        provider_label="Test roads",
        _encode_polyline=lambda coordinates: "combined" if coordinates else "",
    )
    trip = SimpleNamespace(
        id=uuid4(),
        start_location="Colombo",
        destination="Ella",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 11),
        transport_type="car",
        travelers=2,
    )
    places = [
        SimpleNamespace(
            place_key="ella_rock",
            name="Ella Rock",
            category="nature",
            best_time_to_visit="morning",
            opening_hours=None,
            availability_warnings=[],
            estimated_visit_duration_hours=2,
            priority_score=8,
            latitude=6.8563,
            longitude=81.0577,
        )
    ]
    hotels = [
        SimpleNamespace(
            name="Day One Hotel",
            day_number=1,
            latitude=6.8700,
            longitude=81.0500,
            check_in_date=None,
            check_out_date=None,
        ),
        SimpleNamespace(
            name="Day Two Hotel",
            day_number=2,
            latitude=6.8800,
            longitude=81.0600,
            check_in_date=None,
            check_out_date=None,
        ),
    ]

    result = agent.generate_route_plan(
        trip=trip,
        selected_places=places,
        selected_hotels=hotels,
        request=RoutePlanRequest(
            include_hotels=True,
            return_to_hotel=True,
            return_to_start_location=True,
        ),
    )

    assert result.days[0].segments[-1].to_name == "Day One Hotel"
    assert result.days[1].stops == []
    assert [segment.to_name for segment in result.days[1].segments] == [
        "Day Two Hotel",
        "Colombo",
    ]
    assert result.days[1].end_point_name == "Colombo"
    assert any(
        point.latitude == 6.88 and point.longitude == 81.06
        for point in result.days[1].day_path_coordinates
    )
