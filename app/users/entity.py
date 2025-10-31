from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, unique=True, nullable=False)
    phonenumber = Column(String, nullable=True, unique=True)
    password = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False) # default is not verified
    role = Column(String, nullable=False, default="user") # default is user
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # New health-related fields (optional)
    dob = Column(Date, nullable=True, default=None)  # Date of Birth
    sex = Column(Integer, nullable=True, default=None)
    cp = Column(Integer, nullable=True, default=None)
    trestbps = Column(Integer, nullable=True, default=None)
    exang = Column(Integer, nullable=True, default=None)
    
    # Relationship to OTP (defined in auth module)
    otps = relationship("OTP", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship to Prediction
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")