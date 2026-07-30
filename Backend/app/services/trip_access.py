from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.trip import Trip
from app.models.trip_collaborator import TripCollaborator


def require_trip_access(
    db: Session,
    trip_id: UUID,
    user_id: UUID,
    *,
    write: bool = False,
    owner_only: bool = False,
) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id == user_id:
        return trip
    if owner_only:
        raise HTTPException(status_code=404, detail="Trip not found")

    collaboration = db.query(TripCollaborator).filter(
        TripCollaborator.trip_id == trip_id,
        TripCollaborator.user_id == user_id,
    ).first()
    if not collaboration:
        raise HTTPException(status_code=404, detail="Trip not found")
    if write and collaboration.role != "editor":
        raise HTTPException(status_code=403, detail="This shared trip is read-only for your account")
    return trip

