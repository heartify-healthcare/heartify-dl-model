from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any, Tuple
import bcrypt
from app.users.repository import UserRepository
from app.users.entity import User
from app.users.schema import UserCreateSchema, UserUpdateSchema, UserHealthUpdateSchema

class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def create_user(self, data: UserCreateSchema) -> Tuple[Optional[User], Optional[Dict[str, str]]]:
        """Create a new user - typically called by admin"""
        # Check if username already exists
        if self.repo.get_by_username(data.username):
            return None, {"error": "Username already exists"}
            
        # Check if email already exists
        if self.repo.get_by_email(data.email):
            return None, {"error": "Email already exists"}
            
        # Check if phonenumber already exists
        if data.phonenumber and self.repo.get_by_phonenumber(data.phonenumber):
            return None, {"error": "Phone number already exists"}
        
        # Hash password before storing
        hashed_password = self._hash_password(data.password)
        
        user = User(
            username=data.username,
            email=data.email,
            phonenumber=data.phonenumber,
            password=hashed_password,
            role=data.role,
            is_verified=True,  # Admin-created users are automatically verified
            # Health fields default to None
            dob=None,
            sex=None,
            cp=None,
            trestbps=None,
            exang=None
        )
        return self.repo.create(user), None

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.repo.get_by_id(user_id)

    def list_users(self) -> List[User]:
        """List all users - admin only"""
        return self.repo.get_all()

    def update_user(self, user_id: int, data: UserUpdateSchema, current_user_role: str = "user") -> Tuple[Optional[User], Optional[Dict[str, str]]]:
        """Update user with role-based restrictions"""
        user = self.repo.get_by_id(user_id)
        if not user:
            return None, {"error": "User not found"}
            
        update_data = data.dict(exclude_unset=True)
        
        # Regular users cannot update role or is_verified fields
        if current_user_role != 'admin':
            # Remove admin-only fields from update data
            restricted_fields = ['role', 'is_verified']
            for field in restricted_fields:
                if field in update_data:
                    update_data.pop(field)
        
        # Validate unique constraints before updating
        validation_error = self._validate_unique_fields(user, update_data)
        if validation_error:
            return None, validation_error
        
        # Hash password if it's being updated
        if "password" in update_data:
            update_data["password"] = self._hash_password(update_data["password"])
        
        # Apply updates
        for key, value in update_data.items():
            setattr(user, key, value)
            
        return self.repo.update(user), None

    def update_user_health(self, user_id: int, data: UserHealthUpdateSchema) -> Tuple[Optional[User], Optional[Dict[str, str]]]:
        """Update user health fields only"""
        user = self.repo.get_by_id(user_id)
        if not user:
            return None, {"error": "User not found"}
            
        update_data = data.dict(exclude_unset=True)
        
        # Apply health field updates
        for key, value in update_data.items():
            setattr(user, key, value)
            
        return self.repo.update(user), None

    def _validate_unique_fields(self, user: User, update_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Validate unique constraints for update operations"""
        # Check if username is being updated and already exists
        if "username" in update_data and update_data["username"] != user.username:
            if self.repo.get_by_username(update_data["username"]):
                return {"error": "Username already exists"}
                
        # Check if email is being updated and already exists
        if "email" in update_data and update_data["email"] != user.email:
            if self.repo.get_by_email(update_data["email"]):
                return {"error": "Email already exists"}
                
        # Check if phonenumber is being updated and already exists
        if "phonenumber" in update_data and update_data["phonenumber"] != user.phonenumber:
            if update_data["phonenumber"] and self.repo.get_by_phonenumber(update_data["phonenumber"]):
                return {"error": "Phone number already exists"}
        
        return None

    def delete_user(self, user_id: int) -> bool:
        """Delete user - admin only"""
        user = self.repo.get_by_id(user_id)
        if user:
            self.repo.delete(user)
            return True
        return False

    def change_user_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, Optional[Dict[str, str]]]:
        """Change user password with old password verification"""
        user = self.repo.get_by_id(user_id)
        if not user:
            return False, {"error": "User not found"}
        
        # Verify old password
        if not self._verify_password(old_password, user.password):
            return False, {"error": "Current password is incorrect"}
        
        # Update password
        user.password = self._hash_password(new_password)
        self.repo.update(user)
        
        return True, None

    def get_user_statistics(self) -> Dict[str, int]:
        """Get user statistics - admin only"""
        all_users = self.repo.get_all()
        verified_users = [u for u in all_users if u.is_verified]
        admin_users = [u for u in all_users if u.role == 'admin']
        users_with_health_data = self.repo.get_users_with_health_data()
        
        return {
            "total_users": len(all_users),
            "verified_users": len(verified_users),
            "unverified_users": len(all_users) - len(verified_users),
            "admin_users": len(admin_users),
            "regular_users": len(all_users) - len(admin_users),
            "users_with_health_data": len(users_with_health_data)
        }