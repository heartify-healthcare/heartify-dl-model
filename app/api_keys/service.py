"""Service layer for API Key business logic"""
import secrets
import uuid
from sqlalchemy.orm import Session
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from app.api_keys.entity import ApiKey
from app.api_keys.repository import ApiKeyRepository


# In-memory store for verification tokens (in production, use Redis or database)
verification_tokens = {}


class ApiKeyService:
    """Business logic for API key management"""
    
    def __init__(self, db: Session):
        self.repo = ApiKeyRepository(db)
    
    def create_verification_token(self, email: str, action: str = "generate") -> str:
        """
        Create a verification token for email verification
        
        Args:
            email: Email address to verify
            action: Either "generate" or "deactivate"
        
        Returns:
            Verification token string
        """
        token = str(uuid.uuid4())
        verification_tokens[token] = {
            "email": email,
            "action": action,
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }
        return token
    
    def verify_token(self, token: str) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
        """
        Verify a token and get the associated email and action
        
        Args:
            token: Verification token
        
        Returns:
            Tuple of (email, action, error_dict)
        """
        if token not in verification_tokens:
            return None, None, {"error": "Invalid or expired token"}
        
        token_data = verification_tokens[token]
        
        # Check if token is expired
        if datetime.utcnow() > token_data["expires_at"]:
            del verification_tokens[token]
            return None, None, {"error": "Token has expired"}
        
        email = token_data["email"]
        action = token_data["action"]
        
        # Remove token after verification
        del verification_tokens[token]
        
        return email, action, None
    
    def generate_api_key_for_email(self, email: str) -> Tuple[Optional[ApiKey], Optional[Dict]]:
        """
        Generate a new API key for an email address
        
        Args:
            email: Email address of the owner
        
        Returns:
            Tuple of (ApiKey, error_dict)
        """
        # Deactivate all existing keys for this email (safety measure)
        self.repo.deactivate_all_for_email(email)
        
        # Generate a secure random API key
        new_key = secrets.token_urlsafe(32)
        
        # Create ApiKey entity
        api_key = ApiKey(
            api_key=new_key,
            email=email,
            active=True
        )
        
        try:
            created_key = self.repo.create(api_key)
            return created_key, None
        except Exception as e:
            return None, {"error": f"Failed to create API key: {str(e)}"}
    
    def deactivate_api_key_for_email(self, email: str) -> Tuple[bool, Optional[Dict]]:
        """
        Deactivate the active API key for an email address
        
        Args:
            email: Email address of the owner
        
        Returns:
            Tuple of (success_bool, error_dict)
        """
        # Get the active API key for this email
        active_key = self.repo.get_active_by_email(email)
        if not active_key:
            return False, {"error": "No active API key found for this email"}
        
        # Deactivate the key
        self.repo.update_active_status(active_key.api_key, False)
        return True, None
    
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
