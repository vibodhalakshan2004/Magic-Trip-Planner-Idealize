from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.main import app
from app.models.budget_estimate import BudgetEstimate
from app.models.preference import Preference
from app.models.review import Review
from app.models.route_plan import RoutePlan
from app.models.selected_hotel import SelectedHotel
from app.models.selected_place import SelectedPlace
from app.models.trip import Trip
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.media_lookup import MediaLookupService


class FakeQuery:
    def __init__(self, db, model):
        self.db = db
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        if self.model is Trip:
            return self.db.trip

        if self.model is User:
            return self.db.user

        if self.model is Preference:
            return self.db.preference

        if self.model is RoutePlan:
            return self.db.route_plan

        if self.model is BudgetEstimate:
            return self.db.budget_estimate

        return None

    def all(self):
        if self.model is Trip:
            return [self.db.trip]

        if self.model is SelectedPlace:
            return self.db.selected_places

        if self.model is SelectedHotel:
            return self.db.selected_hotels

        if self.model is Review:
            return self.db.reviews

        return []


class FakeDB:
    def __init__(self):
        user_id = uuid4()
        trip_id = uuid4()

        self.user = SimpleNamespace(
            id=user_id,
            name="Test User",
            email="test@example.com",
            password_hash=hash_password("StrongPass!2026"),
            profile_picture=None,
            profile_picture_content_type=None,
            profile_picture_version=None,
            profile_picture_updated_at=None,
        )
        self.trip = SimpleNamespace(
            id=trip_id,
            user_id=user_id,
            start_location="Colombo",
            destination="Ella",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 3),
            budget_min=10000,
            budget_max=200000,
            travelers=2,
            transport_type="car",
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
            traveler_notes="",
            emergency_contact="",
            checklist=[],
            expenses=[],
        )
        self.preference = None
        self.selected_places = [
            SimpleNamespace(
                id=uuid4(),
                trip_id=trip_id,
                place_key="nine_arch_bridge",
                name="Nine Arch Bridge",
                category="historical",
                source="user_added",
                short_description="Railway bridge in Ella.",
                reason_for_recommendation="Good scenic stop.",
                best_time_to_visit="morning",
                opening_hours=None,
                availability_warnings=[],
                estimated_visit_duration_hours=1.5,
                estimated_cost_lkr_per_person=0,
                priority_score=8,
                suitable_for=["photography"],
                warnings=[],
                search_query="Nine Arch Bridge Ella Sri Lanka",
                weather_summary=None,
                latitude=6.8768,
                longitude=81.0608,
                image_url="https://example.com/place.jpg",
            )
        ]
        self.selected_hotels = [
            SimpleNamespace(
                id=uuid4(),
                trip_id=trip_id,
                hotel_key="test_hotel",
                name="Test Hotel",
                short_description="Hotel near Ella.",
                hotel_type="hotel",
                source="user_added",
                area="Ella",
                check_in_date=None,
                check_out_date=None,
                nights=2,
                rooms=1,
                estimated_price_per_night_lkr=15000,
                total_estimated_price_lkr=30000,
                rating_estimate=4.2,
                latitude=6.87,
                longitude=81.05,
                distance_summary=None,
                reason_for_recommendation="Close to selected places.",
                amenities=["wifi"],
                warnings=[],
                search_query="Test Hotel Ella Sri Lanka",
                image_url="https://example.com/hotel.jpg",
            )
        ]
        self.route_plan = SimpleNamespace(
            id=uuid4(),
            trip_id=trip_id,
            total_distance_km=12.5,
            total_travel_time_minutes=32.0,
            full_encoded_polyline="abc",
            days=[],
            created_at=datetime(2026, 1, 2),
        )
        self.budget_estimate = SimpleNamespace(
            id=uuid4(),
            trip_id=trip_id,
            days=3,
            nights=2,
            travelers=2,
            budget_min_lkr=10000.0,
            budget_max_lkr=200000.0,
            selected_places_cost_lkr=0.0,
            hotel_cost_lkr=30000.0,
            food_cost_lkr=15000.0,
            transport_cost_lkr=24000.0,
            other_cost_lkr=5000.0,
            subtotal_lkr=74000.0,
            buffer_lkr=7400.0,
            total_estimated_cost_lkr=81400.0,
            remaining_budget_lkr=118600.0,
            over_budget_amount_lkr=0.0,
            budget_status="within_budget",
            breakdown=[],
            warnings=[],
            suggestions=[],
            summary="The trip is estimated to stay within budget.",
            created_at=datetime(2026, 1, 3),
        )
        self.reviews = []

    def query(self, model):
        return FakeQuery(self, model)

    def execute(self, statement):
        return None

    def commit(self):
        return None

    def refresh(self, instance):
        return None


def test_openapi_exposes_planner_restore_endpoints():
    client = TestClient(app)
    schema = client.get("/openapi.json").json()

    expected_paths = {
        "/health",
        "/trips/",
        "/trips/{trip_id}",
        "/trips/{trip_id}/toolkit",
        "/destination/trips/{trip_id}/selected-places",
        "/hotels/trips/{trip_id}/selected-hotels",
        "/routes/trips/{trip_id}/latest",
        "/budget/trips/{trip_id}/latest",
        "/planning/trips/{trip_id}/jobs",
        "/planning/trips/{trip_id}/jobs/latest",
        "/planning/jobs/{job_id}/cancel",
        "/planning/jobs/{job_id}/retry",
        "/planning/trips/{trip_id}/versions",
        "/collaboration/trips/{trip_id}",
        "/auth/me",
        "/auth/me/password",
        "/auth/me/profile-picture",
    }

    assert expected_paths.issubset(schema["paths"].keys())


def test_planner_restore_endpoints_return_saved_state():
    fake_db = FakeDB()

    def override_db():
        yield fake_db

    def override_user():
        return fake_db.user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    try:
        client = TestClient(app)
        trip_id = fake_db.trip.id

        assert client.get("/health").json() == {
            "status": "ok",
            "database": "ok",
        }
        assert client.get("/trips/").json()[0]["id"] == str(trip_id)
        assert client.get(f"/trips/{trip_id}").json()["destination"] == "Ella"
        toolkit = client.put(
            f"/trips/{trip_id}/toolkit",
            json={
                "traveler_notes": "Window seats preferred",
                "emergency_contact": "Family: +94 00 000 0000",
                "checklist": [
                    {"id": "passport", "label": "Pack passport", "completed": True}
                ],
                "expenses": [
                    {
                        "id": "train",
                        "description": "Train tickets",
                        "amount_lkr": 2400,
                        "category": "transport",
                        "paid_by": "Alex",
                        "expense_date": "2026-07-01",
                    }
                ],
            },
        )
        assert toolkit.status_code == 200
        assert toolkit.json()["total_expenses_lkr"] == 2400
        assert client.get(
            f"/trips/{trip_id}/toolkit"
        ).json()["checklist"][0]["completed"] is True
        assert client.get(
            f"/destination/trips/{trip_id}/selected-places"
        ).json()[0]["image_url"] == "https://example.com/place.jpg"
        assert client.get(
            f"/hotels/trips/{trip_id}/selected-hotels"
        ).json()[0]["image_url"] == "https://example.com/hotel.jpg"
        assert client.get(
            f"/routes/trips/{trip_id}/latest"
        ).json()["total_distance_km"] == 12.5
        assert client.get(
            f"/budget/trips/{trip_id}/latest"
        ).json()["budget_status"] == "within_budget"

    finally:
        app.dependency_overrides.clear()


def test_media_relevance_guard_rejects_unrelated_titles():
    service = MediaLookupService()

    assert service._is_relevant_title(
        "Nine Arch Bridge Ella Sri Lanka",
        "Nine Arches Bridge, Demodara",
    )
    assert not service._is_relevant_title(
        "EKHO Ella, Ella, Sri Lanka",
        "List of archaeologists",
    )


def test_media_lookup_prefers_summary_thumbnail(monkeypatch):
    service = MediaLookupService()
    monkeypatch.setattr(service, "_search_title", lambda _query: "Galle Fort")
    monkeypatch.setattr(
        "app.services.media_lookup.map_http_client.get_json",
        lambda *_args, **_kwargs: {
            "thumbnail": {"source": "https://upload.wikimedia.org/galle-320.jpg"},
            "originalimage": {"source": "https://upload.wikimedia.org/galle-6000.jpg"},
            "extract": "Historic fort.",
        },
    )

    media = service.lookup_media("Galle Fort Sri Lanka")

    assert media["image_url"] == "https://upload.wikimedia.org/galle-320.jpg"


def test_commons_lookup_requests_and_uses_thumbnail(monkeypatch):
    service = MediaLookupService()
    captured = {}

    def fake_get_json(*_args, **kwargs):
        captured.update(kwargs["params"])
        return {
            "query": {
                "pages": {
                    "1": {
                        "imageinfo": [
                            {
                                "mime": "image/jpeg",
                                "url": "https://upload.wikimedia.org/original.jpg",
                                "thumburl": "https://upload.wikimedia.org/thumb-1200.jpg",
                            }
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(
        "app.services.media_lookup.map_http_client.get_json",
        fake_get_json,
    )

    image_url = service._search_commons_image("Mirissa Beach")

    assert captured["iiurlwidth"] == 1200
    assert image_url == "https://upload.wikimedia.org/thumb-1200.jpg"


def test_media_lookup_uses_representative_photo_when_exact_place_has_none(monkeypatch):
    service = MediaLookupService()
    monkeypatch.setattr(service, "_search_title", lambda _query: None)
    searched = []

    def fake_commons(query):
        searched.append(query)
        if query == "tea estate Sri Lanka":
            return "https://upload.wikimedia.org/tea-estate-1280.jpg"
        return None

    monkeypatch.setattr(service, "_search_commons_image", fake_commons)

    media = service.lookup_media("Handunugoda Tea Estate Sri Lanka")

    assert "Handunugoda Tea Estate Sri Lanka" in searched
    assert "tea estate Sri Lanka" in searched
    assert media["image_url"] == "https://upload.wikimedia.org/tea-estate-1280.jpg"
    assert media["description"] is None


def test_auth_tokens_and_password_limits_are_safe():
    password_hash = hash_password("StrongPass!2026")

    assert verify_password("StrongPass!2026", password_hash)
    assert not verify_password("x" * 500, password_hash)

    token = create_access_token({"sub": "test-user-id"})
    assert verify_token(token)["sub"] == "test-user-id"

    with pytest.raises(ValidationError):
        UserCreate(
            name="Test User",
            email="test@example.com",
            password="short",
        )


def test_login_uses_http_only_cookie_and_logout_clears_it():
    fake_db = FakeDB()

    def override_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        login = client.post(
            "/auth/login",
            data={"username": fake_db.user.email, "password": "StrongPass!2026"},
        )
        assert login.status_code == 200
        assert "HttpOnly" in login.headers["set-cookie"]
        assert client.get("/auth/me").status_code == 200
        assert client.post("/auth/logout").status_code == 200
        assert client.get("/auth/me").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_profile_details_password_and_picture_can_be_updated():
    fake_db = FakeDB()

    def override_db():
        yield fake_db

    def override_user():
        return fake_db.user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    try:
        client = TestClient(app)

        details = client.patch(
            "/auth/me",
            json={"name": "Updated Traveler", "email": "UPDATED@example.com"},
        )
        assert details.status_code == 200
        assert details.json()["name"] == "Updated Traveler"
        assert details.json()["email"] == "updated@example.com"

        assert client.put(
            "/auth/me/password",
            json={"current_password": "wrong", "new_password": "NewStrongPass!2026"},
        ).status_code == 400
        password = client.put(
            "/auth/me/password",
            json={
                "current_password": "StrongPass!2026",
                "new_password": "NewStrongPass!2026",
            },
        )
        assert password.status_code == 200
        assert verify_password("NewStrongPass!2026", fake_db.user.password_hash)

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"profile-image"
        upload = client.put(
            "/auth/me/profile-picture",
            files={"picture": ("avatar.png", image_bytes, "image/png")},
        )
        assert upload.status_code == 200
        assert upload.json()["profile_picture_version"]

        picture = client.get("/auth/me/profile-picture")
        assert picture.status_code == 200
        assert picture.content == image_bytes
        assert picture.headers["content-type"] == "image/png"
        assert client.get(
            "/auth/me/profile-picture",
            headers={"If-None-Match": picture.headers["etag"]},
        ).status_code == 304

        deleted = client.delete("/auth/me/profile-picture")
        assert deleted.status_code == 200
        assert deleted.json()["profile_picture_version"] is None
        assert client.get("/auth/me/profile-picture").status_code == 404
    finally:
        app.dependency_overrides.clear()
