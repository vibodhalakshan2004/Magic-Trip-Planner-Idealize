from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.routes.budget import calculate_budget_for_trip
from app.api.routes.destination import select_places_for_trip, suggest_places_for_trip
from app.api.routes.hotels import (
    select_hotel_for_route_day,
    suggest_hotels_for_route_day,
)
from app.api.routes.route_plan import (
    confirm_latest_route_for_trip,
    generate_route_for_trip,
)
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.planning_job import PlanningJob
from app.models.trip import Trip
from app.models.user import User
from app.schemas.budget import BudgetCalculateRequest
from app.schemas.destination import DestinationSuggestRequest
from app.schemas.hotel import DailyHotelSelectRequest, DailyHotelSuggestRequest
from app.schemas.route import RoutePlanRequest
from app.schemas.selected_place import SelectPlacesRequest
from app.services.trip_versions import capture_trip_version

logger = logging.getLogger("magictrip.worker")


class JobCancelled(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _update(db: Session, job: PlanningJob, progress: int, stage: str) -> None:
    db.refresh(job)
    if job.cancel_requested:
        raise JobCancelled
    job.progress = progress
    job.current_stage = stage
    job.updated_at = _now()
    db.commit()


def _run_full_plan(db: Session, job: PlanningJob) -> dict:
    user = db.query(User).filter(User.id == job.user_id).one()
    trip = db.query(Trip).filter(Trip.id == job.trip_id).one()
    payload = job.payload or {}

    capture_trip_version(db, trip, "Before automatic planning")
    _update(db, job, 8, "Generating destination ideas")
    destination = suggest_places_for_trip(
        trip.id,
        DestinationSuggestRequest(
            use_saved_preferences=bool(payload.get("use_saved_preferences", True)),
            interests=payload.get("interests", []),
            trip_style=payload.get("trip_style", "balanced"),
            special_notes=payload.get("special_notes") or None,
        ),
        db,
        user,
    )
    max_places = int(payload.get("max_places", 6))
    places = sorted(destination.suggested_places, key=lambda item: item.priority_score, reverse=True)[:max_places]

    _update(db, job, 25, "Saving the best-matched places")
    select_places_for_trip(
        trip.id,
        SelectPlacesRequest(selected_places=[item.model_dump(mode="json") for item in places]),
        db,
        user,
    )

    _update(db, job, 42, "Building the day-by-day route")
    route = generate_route_for_trip(trip.id, RoutePlanRequest(), db, user)
    confirm_latest_route_for_trip(trip.id, db, user)

    hotel_days = max(len(route.days) - 1, 0)
    selected_hotel_days: list[int] = []
    for index, day_number in enumerate(range(1, hotel_days + 1)):
        progress = 50 + round((index / max(hotel_days, 1)) * 25)
        _update(db, job, progress, f"Finding a stay near day {day_number}'s final stop")
        suggestions = suggest_hotels_for_route_day(
            trip.id,
            day_number,
            DailyHotelSuggestRequest(
                hotel_type=payload.get("hotel_type", "any"),
                hotel_preference=payload.get("hotel_preference") or None,
                rooms=int(payload.get("rooms", 1)),
                max_results=5,
                radius_km=20,
            ),
            db,
            user,
        )
        if suggestions["suggestions"]:
            select_hotel_for_route_day(
                trip.id,
                day_number,
                DailyHotelSelectRequest(hotel=suggestions["suggestions"][0]),
                db,
                user,
            )
            selected_hotel_days.append(day_number)

    _update(db, job, 78, "Adding stays to the route")
    if selected_hotel_days:
        generate_route_for_trip(
            trip.id,
            RoutePlanRequest(
                include_hotels=True,
                return_to_hotel=True,
                return_to_start_location=True,
            ),
            db,
            user,
        )

    _update(db, job, 90, "Calculating the trip budget")
    budget = calculate_budget_for_trip(
        trip.id,
        BudgetCalculateRequest(
            food_cost_per_person_per_day_lkr=float(
                payload.get("food_cost_per_person_per_day_lkr", 2500)
            ),
            shopping_other_cost_lkr=float(payload.get("shopping_other_cost_lkr", 0)),
        ),
        db,
        user,
    )

    _update(db, job, 97, "Saving a restorable trip version")
    version = capture_trip_version(db, trip, "Automatic plan completed")
    return {
        "trip_id": str(trip.id),
        "selected_places": len(places),
        "selected_hotel_days": selected_hotel_days,
        "budget_status": budget.budget_status,
        "version_id": str(version.id),
    }


def claim_next_job(db: Session) -> PlanningJob | None:
    job = (
        db.query(PlanningJob)
        .filter(PlanningJob.status == "queued", PlanningJob.cancel_requested.is_(False))
        .order_by(PlanningJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if not job:
        return None
    job.status = "running"
    job.started_at = _now()
    job.attempts += 1
    db.commit()
    db.refresh(job)
    return job


def process_job(db: Session, job: PlanningJob) -> None:
    try:
        result = _run_full_plan(db, job)
        db.refresh(job)
        job.status = "completed"
        job.progress = 100
        job.current_stage = "Plan ready"
        job.result = result
        job.completed_at = _now()
        db.commit()
    except JobCancelled:
        db.rollback()
        db.refresh(job)
        job.status = "cancelled"
        job.current_stage = "Cancelled"
        job.completed_at = _now()
        db.commit()
    except HTTPException as error:
        db.rollback()
        db.refresh(job)
        job.status = "failed"
        job.current_stage = "Planning failed"
        job.error = str(error.detail)
        job.completed_at = _now()
        db.commit()
    except Exception:
        logger.exception("Planning job %s failed", job.id)
        db.rollback()
        db.refresh(job)
        job.status = "failed"
        job.current_stage = "Planning failed"
        job.error = "The planner could not finish this trip. A checkpoint from before automatic planning is available in version history."
        job.completed_at = _now()
        db.commit()


def run_forever() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Planning worker started")
    while True:
        with SessionLocal() as db:
            job = claim_next_job(db)
            if job:
                process_job(db, job)
                continue
        time.sleep(settings.PLANNING_WORKER_POLL_SECONDS)


if __name__ == "__main__":
    run_forever()
