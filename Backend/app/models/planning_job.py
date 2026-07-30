import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class PlanningJob(Base):
    __tablename__ = "planning_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_planning_jobs_user_idempotency"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(40), nullable=False, default="full_plan")
    status = Column(String(20), nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    current_stage = Column(String(120), nullable=False, default="Queued")
    payload = Column(JSONB, nullable=False, default=dict)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    idempotency_key = Column(String(120), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
