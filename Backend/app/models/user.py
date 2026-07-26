from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import UUID


import uuid

from datetime import datetime

from app.core.database import Base



class User(Base):

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name = Column(
        String,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    trips = relationship(
    "Trip",
    back_populates="user"
    )

    preferences = relationship(
    "Preference",
    back_populates="user",
    uselist=False
    )
    
    reviews = relationship(
    "Review",
    back_populates="user"
    )