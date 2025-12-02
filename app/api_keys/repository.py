from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from app.api_keys.entity import ApiKey


class ApiKeyRepository:
    """Handles database operations for API Keys."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, api_key: ApiKey) -> ApiKey:
        """Create a new API key in database."""
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key
    
    def get_by_key(self, key: str) -> Optional[ApiKey]:
        """Retrieve an API key by its key string."""
        return self.db.query(ApiKey).filter(ApiKey.api_key == key).first()
    
    def get_by_email(self, email: str) -> List[ApiKey]:
        """Retrieve all API keys for a given email address."""
        return self.db.query(ApiKey).filter(ApiKey.email == email).all()
    
    def get_active_by_email(self, email: str) -> Optional[ApiKey]:
        """Retrieve the active API key for a given email address."""
        return self.db.query(ApiKey).filter(
            ApiKey.email == email,
            ApiKey.active == True
        ).first()
    
    def update_active_status(self, key: str, active: bool) -> Optional[ApiKey]:
        """Update the active status of an API key."""
        api_key = self.get_by_key(key)
        if api_key:
            api_key.active = active
            self.db.commit()
            self.db.refresh(api_key)
        return api_key
    
    def deactivate_all_for_email(self, email: str) -> None:
        """Deactivate all API keys for a given email address."""
        api_keys = self.get_by_email(email)
        for api_key in api_keys:
            api_key.active = False
        self.db.commit()
    
    def update_last_used(self, key: str) -> None:
        """Update the last_used timestamp for an API key."""
        api_key = self.get_by_key(key)
        if api_key:
            api_key.last_used = datetime.utcnow()
            self.db.commit()
