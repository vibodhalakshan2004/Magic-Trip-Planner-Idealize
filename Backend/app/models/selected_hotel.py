from datetime import datetime
import uuid

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class SelectedHotel(Base):
    __tablename__ = "selected_hotels"
    __table_args__ = (
        Index("ix_selected_hotels_trip_day", "trip_id", "day_number"),
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

    route_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("route_plans.id", ondelete="SET NULL"),
        nullable=True
    )

    day_number = Column(
        Integer,
        nullable=True
    )

    hotel_key = Column(
        String,
        nullable=False
    )

    name = Column(
        String,
        nullable=False
    )

    short_description = Column(
        String,
        nullable=True
    )

    hotel_type = Column(
        String,
        nullable=False,
        default="hotel"
    )

    source = Column(
        String,
        nullable=False,
        default="ai_suggested"
    )

    area = Column(
        String,
        nullable=True
    )

    check_in_date = Column(
        Date,
        nullable=True
    )

    check_out_date = Column(
        Date,
        nullable=True
    )

    nights = Column(
        Integer,
        nullable=False,
        default=1
    )

    rooms = Column(
        Integer,
        nullable=False,
        default=1
    )

    estimated_price_per_night_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    total_estimated_price_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    rating_estimate = Column(
        Float,
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

    distance_summary = Column(
        String,
        nullable=True
    )

    transfer_distance_km = Column(
        Float,
        nullable=False,
        default=0
    )

    transfer_time_minutes = Column(
        Float,
        nullable=False,
        default=0
    )

    transfer_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    reason_for_recommendation = Column(
        String,
        nullable=True
    )

    amenities = Column(
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

    image_url = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    trip = relationship(
        "Trip",
        back_populates="selected_hotels"
    )
