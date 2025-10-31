"""Repository layer for API Key database operations"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.api_keys.entity import ApiKey


class ApiKeyRepository:
    """Handles database operations for API Keys"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, api_key: ApiKey) -> ApiKey:
        """Create a new API key in database"""
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key
    
    def get_by_key(self, key: str) -> Optional[ApiKey]:
        """Retrieve an API key by its key string"""
        return self.db.query(ApiKey).filter(ApiKey.api_key == key).first()
    
    def update_active_status(self, key: str, active: bool) -> Optional[ApiKey]:
        """Update the active status of an API key"""
        api_key = self.get_by_key(key)
        if api_key:
            api_key.active = active
            self.db.commit()
            self.db.refresh(api_key)
        return api_key
    
    def update_last_used(self, key: str) -> None:
        """Update the last_used timestamp for an API key"""
        api_key = self.get_by_key(key)
        if api_key:
            api_key.last_used = datetime.utcnow()
            self.db.commit()
    
    def delete(self, key: str) -> bool:
        """Delete an API key from database"""
        api_key = self.get_by_key(key)
        if api_key:
            self.db.delete(api_key)
            self.db.commit()
            return True
        return False
