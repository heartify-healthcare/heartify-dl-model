from pydantic import BaseModel, EmailStr, constr, validator
from typing import Optional
from datetime import datetime, date

class UserCreateSchema(BaseModel):
    username: constr(min_length=3)
    email: EmailStr
    phonenumber: Optional[str] = None
    password: constr(min_length=6)
    role: Optional[str] = "user"  # role field with default value
    # Health fields are not included in create - they default to None
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['user', 'admin']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v

    @validator('phonenumber')
    def validate_phonenumber(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None  # Convert empty strings to None
        return v

class UserUpdateSchema(BaseModel):
    username: Optional[constr(min_length=3)] = None
    email: Optional[EmailStr] = None
    phonenumber: Optional[str] = None
    password: Optional[constr(min_length=6)] = None  # Allow password updates
    is_verified: Optional[bool] = None
    role: Optional[str] = None
    # Health-related fields
    dob: Optional[date] = None  # Date of Birth
    sex: Optional[int] = None
    cp: Optional[int] = None
    trestbps: Optional[int] = None
    exang: Optional[int] = None

    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            allowed_roles = ['user', 'admin']
            if v not in allowed_roles:
                raise ValueError(f'Role must be one of: {allowed_roles}')
        return v

    @validator('phonenumber')
    def validate_phonenumber(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None  # Convert empty strings to None
        return v

    @validator('dob')
    def validate_dob(cls, v):
        if v is not None:
            # Check if date is not in the future
            if v > date.today():
                raise ValueError('Date of birth cannot be in the future')
            # Check for reasonable date range (not too old)
            if v.year < 1900:
                raise ValueError('Date of birth cannot be before 1900')
        return v

    @validator('sex')
    def validate_sex(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('Sex must be 0 or 1')
        return v

    @validator('cp')
    def validate_cp(cls, v):
        if v is not None and v not in [1, 2, 3, 4]:
            raise ValueError('CP must be 1, 2, 3, or 4')
        return v

    @validator('trestbps')
    def validate_trestbps(cls, v):
        if v is not None and (v < 50 or v > 300):
            raise ValueError('Trestbps must be between 50 and 300')
        return v

    @validator('exang')
    def validate_exang(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('Exang must be 0 or 1')
        return v

class UserOutSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    phonenumber: Optional[str]
    is_verified: bool
    role: str
    created_at: datetime
    # Health-related fields
    dob: Optional[date] = None  # Date of Birth
    sex: Optional[int] = None
    cp: Optional[int] = None
    trestbps: Optional[int] = None
    exang: Optional[int] = None

    class Config:
        orm_mode = True

class UserProfileSchema(BaseModel):
    """Schema for user profile updates (excludes sensitive fields)"""
    username: Optional[constr(min_length=3)] = None
    email: Optional[EmailStr] = None
    phonenumber: Optional[str] = None

    @validator('phonenumber')
    def validate_phonenumber(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None  # Convert empty strings to None
        return v

class UserHealthUpdateSchema(BaseModel):
    """Schema for updating only health-related fields"""
    dob: Optional[date] = None  # Date of Birth
    sex: Optional[int] = None
    cp: Optional[int] = None
    trestbps: Optional[int] = None
    exang: Optional[int] = None

    @validator('dob')
    def validate_dob(cls, v):
        if v is not None:
            # Check if date is not in the future
            if v > date.today():
                raise ValueError('Date of birth cannot be in the future')
            # Check for reasonable date range (not too old)
            if v.year < 1900:
                raise ValueError('Date of birth cannot be before 1900')
        return v

    @validator('sex')
    def validate_sex(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('Sex must be 0 or 1')
        return v

    @validator('cp')
    def validate_cp(cls, v):
        if v is not None and v not in [1, 2, 3, 4]:
            raise ValueError('CP must be 1, 2, 3, or 4')
        return v

    @validator('trestbps')
    def validate_trestbps(cls, v):
        if v is not None and (v < 50 or v > 300):
            raise ValueError('Trestbps must be between 50 and 300')
        return v

    @validator('exang')
    def validate_exang(cls, v):
        if v is not None and v not in [0, 1]:
            raise ValueError('Exang must be 0 or 1')
        return v

class ChangePasswordSchema(BaseModel):
    current_password: constr(min_length=1)
    new_password: constr(min_length=6)