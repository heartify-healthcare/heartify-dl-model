from sqlalchemy.orm import Session
from typing import Optional, List
from app.users.entity import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
        
    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
        
    def get_by_phonenumber(self, phonenumber: str) -> Optional[User]:
        if phonenumber:
            return self.db.query(User).filter(User.phonenumber == phonenumber).first()
        return None

    def get_all(self) -> List[User]:
        return self.db.query(User).all()

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()

    def get_verified_users_only(self) -> List[User]:
        """Get only verified users - useful for admin operations"""
        return self.db.query(User).filter(User.is_verified == True).all()

    def get_users_by_role(self, role: str) -> List[User]:
        """Get users by role - useful for role-based operations"""
        return self.db.query(User).filter(User.role == role).all()

    def get_users_with_health_data(self) -> List[User]:
        """Get users who have at least one health field populated"""
        return self.db.query(User).filter(
            (User.dob.isnot(None)) |
            (User.sex.isnot(None)) |
            (User.cp.isnot(None)) |
            (User.trestbps.isnot(None)) |
            (User.exang.isnot(None))
        ).all()