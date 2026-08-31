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


class BudgetEstimate(Base):
    __tablename__ = "budget_estimates"
    __table_args__ = (
        Index("ix_budget_estimates_trip_created", "trip_id", "created_at"),
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

    days = Column(
        Integer,
        nullable=False
    )

    nights = Column(
        Integer,
        nullable=False
    )

    travelers = Column(
        Integer,
        nullable=False
    )

    budget_min_lkr = Column(
        Float,
        nullable=False
    )

    budget_max_lkr = Column(
        Float,
        nullable=False
    )

    selected_places_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    hotel_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    food_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    transport_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    other_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    subtotal_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    buffer_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    total_estimated_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    remaining_budget_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    over_budget_amount_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    budget_status = Column(
        String,
        nullable=False
    )

    breakdown = Column(
        JSONB,
        nullable=False,
        default=list
    )

    warnings = Column(
        JSONB,
        nullable=False,
        default=list
    )

    suggestions = Column(
        JSONB,
        nullable=False,
        default=list
    )

    summary = Column(
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
        back_populates="budget_estimates"
    )
