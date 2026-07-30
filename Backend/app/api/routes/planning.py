from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.planning_job import PlanningJob
from app.models.trip_version import TripVersion
from app.models.user import User
from app.schemas.planning import (
    FullPlanJobCreate,
    PlanningJobResponse,
    TripVersionCreate,
    TripVersionResponse,
)
from app.services.trip_access import require_trip_access
from app.services.trip_versions import capture_trip_version, restore_trip_version

router = APIRouter(prefix="/planning", tags=["Planning jobs"])


@router.post(
    "/trips/{trip_id}/jobs",
    response_model=PlanningJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_full_plan_job(
    trip_id: UUID,
    request: FullPlanJobCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=120),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_trip_access(db, trip_id, current_user.id, write=True)
    existing = db.query(PlanningJob).filter(
        PlanningJob.user_id == current_user.id,
        PlanningJob.idempotency_key == idempotency_key,
    ).first()
    if existing:
        return existing

    job = PlanningJob(
        user_id=current_user.id,
        trip_id=trip_id,
        idempotency_key=idempotency_key,
        payload=request.model_dump(mode="json"),
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        job = db.query(PlanningJob).filter(
            PlanningJob.user_id == current_user.id,
            PlanningJob.idempotency_key == idempotency_key,
        ).one()
    db.refresh(job)
    return job


@router.get("/jobs/{job_id}", response_model=PlanningJobResponse)
def get_planning_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(PlanningJob).filter(
        PlanningJob.id == job_id,
        PlanningJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Planning job not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=PlanningJobResponse)
def cancel_planning_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(PlanningJob).filter(
        PlanningJob.id == job_id,
        PlanningJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Planning job not found")
    if job.status not in {"completed", "failed", "cancelled"}:
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.current_stage = "Cancelled"
            job.completed_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(job)
    return job


@router.post("/trips/{trip_id}/versions", response_model=TripVersionResponse)
def create_trip_version(
    trip_id: UUID,
    request: TripVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)
    return capture_trip_version(db, trip, request.label)


@router.get("/trips/{trip_id}/versions", response_model=list[TripVersionResponse])
def list_trip_versions(
    trip_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_trip_access(db, trip_id, current_user.id)
    return db.query(TripVersion).filter(TripVersion.trip_id == trip_id).order_by(
        TripVersion.version_number.desc()
    ).all()


@router.post("/trips/{trip_id}/versions/{version_id}/restore", response_model=TripVersionResponse)
def restore_version(
    trip_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trip = require_trip_access(db, trip_id, current_user.id, write=True)
    version = db.query(TripVersion).filter(
        TripVersion.id == version_id,
        TripVersion.trip_id == trip.id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Trip version not found")
    capture_trip_version(db, trip, f"Before restoring version {version.version_number}")
    restore_trip_version(db, trip, version)
    return version
