from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class ExternalCache(Base):
    __tablename__ = "external_cache"

    cache_key = Column(String(500), primary_key=True)
    payload = Column(JSONB, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
