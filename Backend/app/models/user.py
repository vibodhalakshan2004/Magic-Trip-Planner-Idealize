import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("google_subject", name="uq_users_google_subject"),
    )

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
        nullable=True
    )

    google_subject = Column(
        String(255),
        nullable=True,
    )

    profile_picture = Column(
        LargeBinary,
        nullable=True,
    )

    profile_picture_content_type = Column(
        String(50),
        nullable=True,
    )

    profile_picture_version = Column(
        String(64),
        nullable=True,
    )

    profile_picture_updated_at = Column(
        DateTime,
        nullable=True,
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
