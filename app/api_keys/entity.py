from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ApiKey(Base):
    """API Key entity for managing access to protected endpoints."""
    __tablename__ = "api_keys"

    api_key = Column(String, primary_key=True, nullable=False)
    email = Column(String, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_used = Column(DateTime, nullable=True)
