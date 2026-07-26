from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.trip import Trip
from app.models.user import User

from app.schemas.trip import TripCreate, TripResponse
from app.schemas.toolkit import TripToolkitResponse, TripToolkitUpdate


router = APIRouter(
    prefix="/trips",
    tags=["Trips"],
)


@router.post("/", response_model=TripResponse)
def create_trip(
    trip: TripCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_trip = Trip(
        user_id=current_user.id,
        start_location=trip.start_location,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget_min=trip.budget_min,
        budget_max=trip.budget_max,
        travelers=trip.travelers,
        transport_type=trip.transport_type,
    )

    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    return new_trip


@router.get("/", response_model=list[TripResponse])
def get_my_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Trip)
        .filter(Trip.user_id == current_user.id)
        .order_by(func.coalesce(Trip.updated_at, Trip.created_at).desc(), Trip.created_at.desc())
        .all()
    )


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
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

    return trip


def _owned_trip(trip_id: UUID, db: Session, current_user: User) -> Trip:
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
    return trip


def _toolkit_response(trip: Trip) -> TripToolkitResponse:
    expenses = trip.expenses or []
    return TripToolkitResponse(
        trip_id=str(trip.id),
        traveler_notes=trip.traveler_notes or "",
        emergency_contact=trip.emergency_contact or "",
        checklist=trip.checklist or [],
        expenses=expenses,
        total_expenses_lkr=round(
            sum(float(item.get("amount_lkr", 0)) for item in expenses),
            2,
        ),
    )


@router.get("/{trip_id}/toolkit", response_model=TripToolkitResponse)
def get_trip_toolkit(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _toolkit_response(_owned_trip(trip_id, db, current_user))


@router.put("/{trip_id}/toolkit", response_model=TripToolkitResponse)
def update_trip_toolkit(
    trip_id: UUID,
    toolkit: TripToolkitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = _owned_trip(trip_id, db, current_user)
    trip.traveler_notes = toolkit.traveler_notes.strip()
    trip.emergency_contact = toolkit.emergency_contact.strip()
    trip.checklist = [item.model_dump(mode="json") for item in toolkit.checklist]
    trip.expenses = [item.model_dump(mode="json") for item in toolkit.expenses]
    trip.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(trip)
    return _toolkit_response(trip)


@router.delete("/{trip_id}")
def delete_trip(
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

    db.delete(trip)
    db.commit()

    return {"message": "Trip deleted"}
