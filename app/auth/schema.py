from pydantic import BaseModel, EmailStr, constr
from typing import Optional

class RegisterSchema(BaseModel):
    username: constr(min_length=3)
    email: EmailStr
    phonenumber: Optional[str] = None
    password: constr(min_length=6)

class RequestVerifySchema(BaseModel):
    email: EmailStr

class VerifySchema(BaseModel):
    email: EmailStr
    otp_code: constr(min_length=6, max_length=6)

class LoginSchema(BaseModel):
    username: str
    password: str

class RecoverPasswordSchema(BaseModel):
    username: str
    email: EmailStr
    phone_number: str

class LoginResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class MessageResponseSchema(BaseModel):
    message: str