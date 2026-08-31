from datetime import datetime
import uuid

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Text

from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        Index("ix_trips_user_updated", "user_id", "updated_at"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    start_location = Column(
        String,
        nullable=False
    )

    destination = Column(
        String,
        nullable=False
    )

    start_date = Column(
        Date,
        nullable=False
    )

    end_date = Column(
        Date,
        nullable=False
    )

    budget_min = Column(
        Integer,
        nullable=False
    )

    budget_max = Column(
        Integer,
        nullable=False
    )

    travelers = Column(
        Integer,
        nullable=False,
        default=1
    )

    transport_type = Column(
        String,
        nullable=False,
        default="car"
    )

    traveler_notes = Column(
        Text,
        nullable=False,
        default="",
    )

    emergency_contact = Column(
        Text,
        nullable=False,
        default="",
    )

    checklist = Column(
        JSONB,
        nullable=False,
        default=list,
    )

    expenses = Column(
        JSONB,
        nullable=False,
        default=list,
    )

    trip_status = Column(
        String,
        nullable=False,
        default="draft"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="trips"
    )

    selected_places = relationship(
    "SelectedPlace",
    back_populates="trip",
    cascade="all, delete-orphan"
    )

    selected_hotels = relationship(
    "SelectedHotel",
    back_populates="trip",
    cascade="all, delete-orphan"
    )

    budget_estimates = relationship(
    "BudgetEstimate",
    back_populates="trip",
    cascade="all, delete-orphan"
    )

    route_plans = relationship(
    "RoutePlan",
    back_populates="trip",
    cascade="all, delete-orphan"
    )
