from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.destination import DestinationAgentResponse, SuggestedPlace
from app.workers import planning_worker


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def one(self):
        return self.result


class FakeDB:
    def __init__(self, user, trip):
        self.user = user
        self.trip = trip

    def query(self, model):
        return FakeQuery(self.user if model.__name__ == "User" else self.trip)

    def refresh(self, instance):
        return None

    def commit(self):
        return None


def _place(index: int) -> SuggestedPlace:
    return SuggestedPlace(
        place_key=f"place_{index}",
        name=f"Place {index}",
        category="nature",
        short_description="A test place",
        reason_for_recommendation="Matches the trip",
        best_time_to_visit="morning",
        estimated_visit_duration_hours=1,
        estimated_cost_lkr_per_person=0,
        priority_score=index,
        search_query=f"Place {index}, Sri Lanka",
    )


def test_full_plan_worker_reuses_existing_workflow_without_live_providers(monkeypatch):
    user = SimpleNamespace(id=uuid4())
    trip = SimpleNamespace(id=uuid4(), user_id=user.id)
    job = SimpleNamespace(
        id=uuid4(),
        user_id=user.id,
        trip_id=trip.id,
        payload={"max_places": 3},
        cancel_requested=False,
        progress=0,
        current_stage="Queued",
        updated_at=None,
    )
    calls = []
    destination = DestinationAgentResponse(
        trip_id=str(trip.id),
        destination="Ella",
        summary="Test",
        suggested_places=[_place(1), _place(3), _place(2)],
    )

    monkeypatch.setattr(planning_worker, "suggest_places_for_trip", lambda *args: destination)
    monkeypatch.setattr(planning_worker, "select_places_for_trip", lambda *args: calls.append("places"))
    monkeypatch.setattr(planning_worker, "generate_route_for_trip", lambda *args: SimpleNamespace(days=[1, 2]))
    monkeypatch.setattr(planning_worker, "confirm_latest_route_for_trip", lambda *args: calls.append("confirm"))
    monkeypatch.setattr(planning_worker, "suggest_hotels_for_route_day", lambda *args: {"suggestions": []})
    monkeypatch.setattr(planning_worker, "calculate_budget_for_trip", lambda *args: SimpleNamespace(budget_status="within_budget"))
    version_id = uuid4()
    monkeypatch.setattr(planning_worker, "capture_trip_version", lambda *args: SimpleNamespace(id=version_id))

    result = planning_worker._run_full_plan(FakeDB(user, trip), job)

    assert calls == ["places", "confirm"]
    assert result["selected_places"] == 3
    assert result["selected_hotel_days"] == []
    assert result["version_id"] == str(version_id)
    assert job.progress == 97


def test_worker_honors_cancel_before_next_external_stage():
    job = SimpleNamespace(cancel_requested=True, progress=0, current_stage="Queued", updated_at=None)
    with pytest.raises(planning_worker.JobCancelled):
        planning_worker._update(FakeDB(None, None), job, 10, "Starting")
