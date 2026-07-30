from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class GoogleApiUsage(Base):
    __tablename__ = "google_api_usage"

    period = Column(String(7), primary_key=True)
    sku = Column(String(40), primary_key=True)
    used = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
