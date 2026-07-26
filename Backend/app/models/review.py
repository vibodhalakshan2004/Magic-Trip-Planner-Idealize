from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import relationship

from datetime import datetime

import uuid

from app.core.database import Base


class Review(Base):

    __tablename__ = "reviews"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    place_name = Column(
        String,
        nullable=False
    )

    place_type = Column(
        String,
        nullable=False
    )

    rating = Column(
        Integer,
        nullable=False
    )

    review_text = Column(
        Text,
        nullable=False
    )

    visit_date = Column(
        Date,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="reviews"
    )