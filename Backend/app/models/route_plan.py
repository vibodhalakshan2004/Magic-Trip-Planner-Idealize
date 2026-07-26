from datetime import datetime
import uuid

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class RoutePlan(Base):
    __tablename__ = "route_plans"

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

    total_distance_km = Column(
        Float,
        nullable=False,
        default=0
    )

    total_travel_time_minutes = Column(
        Float,
        nullable=False,
        default=0
    )

    total_transport_cost_lkr = Column(
        Float,
        nullable=False,
        default=0
    )

    route_status = Column(
        String,
        nullable=False,
        default="draft"
    )

    map_provider = Column(
        String,
        nullable=True
    )

    summary = Column(
        Text,
        nullable=True
    )

    full_encoded_polyline = Column(
        Text,
        nullable=True
    )

    days = Column(
        JSONB,
        nullable=False,
        default=list
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    trip = relationship(
        "Trip",
        back_populates="route_plans"
    )
