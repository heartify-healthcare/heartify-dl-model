"""Database entity for API Keys"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class ApiKey(Base):
    """
    API Key entity for managing access to protected endpoints
    
    Attributes:
        api_key: Unique API key string
        email: Email address of the API key owner
        active: Whether the key is currently active
        created_at: Timestamp when the key was created
        last_used: Timestamp when the key was last used
    """
    __tablename__ = "api_keys"

    api_key = Column(String, primary_key=True, nullable=False)
    email = Column(String, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_used = Column(DateTime, nullable=True)
