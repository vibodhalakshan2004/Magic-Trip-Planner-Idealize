import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TripCollaborator(Base):
    __tablename__ = "trip_collaborators"
    __table_args__ = (
        UniqueConstraint("trip_id", "user_id", name="uq_trip_collaborators_trip_user"),
        Index("ix_trip_collaborators_user", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
