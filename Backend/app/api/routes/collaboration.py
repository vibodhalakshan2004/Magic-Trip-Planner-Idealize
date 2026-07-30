from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.trip_collaborator import TripCollaborator
from app.models.user import User
from app.schemas.collaboration import CollaboratorInvite, CollaboratorResponse
from app.services.trip_access import require_trip_access

router = APIRouter(prefix="/collaboration", tags=["Trip collaboration"])


def _response(collaboration: TripCollaborator, user: User) -> dict:
    return {
        "id": collaboration.id,
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": collaboration.role,
        "created_at": collaboration.created_at,
    }


@router.get("/trips/{trip_id}", response_model=list[CollaboratorResponse])
def list_collaborators(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_trip_access(db, trip_id, current_user.id, owner_only=True)
    rows = db.query(TripCollaborator, User).join(User, User.id == TripCollaborator.user_id).filter(
        TripCollaborator.trip_id == trip_id
    ).order_by(TripCollaborator.created_at.asc()).all()
    return [_response(collaboration, user) for collaboration, user in rows]


@router.post("/trips/{trip_id}", response_model=CollaboratorResponse, status_code=status.HTTP_201_CREATED)
def invite_collaborator(
    trip_id: UUID,
    request: CollaboratorInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_trip_access(db, trip_id, current_user.id, owner_only=True)
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="That traveler must create an account before being invited")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="The trip owner already has full access")

    collaboration = db.query(TripCollaborator).filter(
        TripCollaborator.trip_id == trip_id,
        TripCollaborator.user_id == user.id,
    ).first()
    if collaboration:
        collaboration.role = request.role
    else:
        collaboration = TripCollaborator(
            trip_id=trip_id,
            user_id=user.id,
            invited_by_user_id=current_user.id,
            role=request.role,
        )
        db.add(collaboration)
    db.commit()
    db.refresh(collaboration)
    return _response(collaboration, user)


@router.delete("/trips/{trip_id}/{collaboration_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_collaborator(
    trip_id: UUID,
    collaboration_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_trip_access(db, trip_id, current_user.id, owner_only=True)
    collaboration = db.query(TripCollaborator).filter(
        TripCollaborator.id == collaboration_id,
        TripCollaborator.trip_id == trip_id,
    ).first()
    if not collaboration:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    db.delete(collaboration)
    db.commit()

