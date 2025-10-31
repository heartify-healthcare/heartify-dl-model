"""Service layer for API Key business logic"""
import secrets
from sqlalchemy.orm import Session
from typing import Optional, Dict, Tuple
from app.api_keys.entity import ApiKey
from app.api_keys.repository import ApiKeyRepository


class ApiKeyService:
    """Business logic for API key management"""
    
    def __init__(self, db: Session):
        self.repo = ApiKeyRepository(db)
    
    def generate_api_key(self) -> Tuple[ApiKey, None]:
        """
        Generate a new random API key and save to database
        
        Returns:
            Tuple of (ApiKey, error_dict)
        """
        # Generate a secure random API key
        new_key = secrets.token_urlsafe(32)
        
        # Create ApiKey entity
        api_key = ApiKey(
            api_key=new_key,
            active=True
        )
        
        try:
            created_key = self.repo.create(api_key)
            return created_key, None
        except Exception as e:
            return None, {"error": f"Failed to create API key: {str(e)}"}
    
    def activate_api_key(self, key: str, active: bool) -> Tuple[Optional[ApiKey], Optional[Dict]]:
        """
        Activate or deactivate an API key
        
        Args:
            key: The API key string
            active: True to activate, False to deactivate
            
        Returns:
            Tuple of (ApiKey, error_dict)
        """
        # Check if key exists
        existing_key = self.repo.get_by_key(key)
        if not existing_key:
            return None, {"error": "API key not found"}
        
        # Update active status
        updated_key = self.repo.update_active_status(key, active)
        return updated_key, None
    
    def validate_api_key(self, key: str) -> bool:
        """
        Validate if an API key exists and is active
        
        Args:
            key: The API key string
            
        Returns:
            True if key is valid and active, False otherwise
        """
        api_key = self.repo.get_by_key(key)
        if api_key and api_key.active:
            # Update last_used timestamp
            self.repo.update_last_used(key)
            return True
        return False
