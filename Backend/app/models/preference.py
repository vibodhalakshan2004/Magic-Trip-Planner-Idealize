from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import ForeignKey

from sqlalchemy.dialects.postgresql import JSONB, UUID

from sqlalchemy.orm import relationship

import uuid

from app.core.database import Base


class Preference(Base):

    __tablename__ = "preferences"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    travel_style = Column(
        String,
        nullable=True
    )

    food_preference = Column(
        String,
        nullable=True
    )

    interests = Column(
        JSONB,
        nullable=False,
        default=list
    )

    preferred_transport = Column(
        String,
        nullable=True
    )

    preferred_hotel_type = Column(
        String,
        nullable=True
    )

    budget_min = Column(
        Integer,
        nullable=True
    )

    budget_max = Column(
        Integer,
        nullable=True
    )

    user = relationship(
        "User",
        back_populates="preferences"
    )