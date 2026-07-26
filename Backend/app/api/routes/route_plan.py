from uuid import UUID
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.route_agent import RouteAgent

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trip import Trip
from app.models.selected_place import SelectedPlace
from app.models.selected_hotel import SelectedHotel
from app.models.route_plan import RoutePlan

from app.schemas.route import (
    RoutePlanRequest,
    RoutePlanResponse,
    SavedRoutePlanResponse,
)


router = APIRouter(
    prefix="/routes",
    tags=["Route Agent"],
)

logger = logging.getLogger(__name__)


@router.post(
    "/trips/{trip_id}/generate",
    response_model=RoutePlanResponse,
)
def generate_route_for_trip(
    trip_id: UUID,
    request: RoutePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = (
        db.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    selected_places = (
        db.query(SelectedPlace)
        .filter(
            SelectedPlace.trip_id == trip.id,
        )
        .all()
    )

    if not selected_places:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one place before generating route.",
        )

    try:
        agent = RouteAgent()
        selected_hotels = []

        if request.include_hotels:
            selected_hotels = (
                db.query(SelectedHotel)
                .filter(SelectedHotel.trip_id == trip.id)
                .all()
            )

        result = agent.generate_route_plan(
            trip=trip,
            selected_places=selected_places,
            selected_hotels=selected_hotels,
            request=request,
        )
        route_status = "confirmed" if request.include_hotels else "draft"
        result.route_status = route_status

        db.query(RoutePlan).filter(
            RoutePlan.trip_id == trip.id
        ).delete(synchronize_session=False)

        route_plan = RoutePlan(
            trip_id=trip.id,
            total_distance_km=result.total_distance_km,
            total_travel_time_minutes=result.total_travel_time_minutes,
            total_transport_cost_lkr=result.total_transport_cost_lkr,
            route_status=route_status,
            map_provider=result.map_provider,
            summary=result.summary,
            full_encoded_polyline=result.full_encoded_polyline,
            days=[
                day.model_dump(mode="json")
                for day in result.days
            ],
        )

        db.add(route_plan)
        trip.updated_at = datetime.utcnow()
        db.commit()

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception:
        logger.exception("Route generation failed for trip %s", trip_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the route plan right now.",
        )


@router.post(
    "/trips/{trip_id}/confirm",
    response_model=SavedRoutePlanResponse,
)
def confirm_latest_route_for_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = (
        db.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    route_plan = (
        db.query(RoutePlan)
        .filter(RoutePlan.trip_id == trip.id)
        .order_by(RoutePlan.created_at.desc())
        .first()
    )

    if not route_plan:
        raise HTTPException(status_code=404, detail="Route plan not found")

    route_plan.route_status = "confirmed"
    trip.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(route_plan)

    return route_plan


@router.get(
    "/trips/{trip_id}/latest",
    response_model=SavedRoutePlanResponse,
)
def get_latest_route_for_trip(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = (
        db.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found",
        )

    route_plan = (
        db.query(RoutePlan)
        .filter(RoutePlan.trip_id == trip.id)
        .order_by(RoutePlan.created_at.desc())
        .first()
    )

    if not route_plan:
        raise HTTPException(
            status_code=404,
            detail="Route plan not found",
        )

    return route_plan
