from datetime import datetime
import uuid

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Float
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class SelectedPlace(Base):
    __tablename__ = "selected_places"
    __table_args__ = (
        Index("ix_selected_places_trip", "trip_id"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    trip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False
    )

    place_key = Column(
        String,
        nullable=False
    )

    name = Column(
        String,
        nullable=False
    )

    category = Column(
        String,
        nullable=False
    )

    source = Column(
    String,
    nullable=False,
    default="ai_suggested"
    )

    short_description = Column(
        String,
        nullable=True
    )

    reason_for_recommendation = Column(
        String,
        nullable=True
    )

    best_time_to_visit = Column(
        String,
        nullable=True
    )

    opening_hours = Column(
        String,
        nullable=True
    )

    availability_warnings = Column(
        JSONB,
        nullable=False,
        default=list
    )

    estimated_visit_duration_hours = Column(
        Float,
        nullable=False,
        default=1.0
    )

    estimated_cost_lkr_per_person = Column(
        Float,
        nullable=False,
        default=0
    )

    priority_score = Column(
        Integer,
        nullable=False,
        default=5
    )

    suitable_for = Column(
        JSONB,
        nullable=False,
        default=list
    )

    warnings = Column(
        JSONB,
        nullable=False,
        default=list
    )

    search_query = Column(
        String,
        nullable=True
    )

    weather_summary = Column(
        String,
        nullable=True
    )

    image_url = Column(
        String,
        nullable=True
    )

    latitude = Column(
    Float,
    nullable=True
    )

    longitude = Column(
    Float,
    nullable=True
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    trip = relationship(
        "Trip",
        back_populates="selected_places"
    )
