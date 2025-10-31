from sqlalchemy.orm import Session
from typing import Optional
from app.auth.entity import OTP
import time

class OTPRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, otp: OTP) -> OTP:
        self.db.add(otp)
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def get_by_user_and_code(self, user_id: int, otp_code: str) -> Optional[OTP]:
        return self.db.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.otp_code == otp_code,
            OTP.otp_used == False,
            OTP.expired_time > int(time.time())
        ).first()

    def get_latest_by_user(self, user_id: int) -> Optional[OTP]:
        return self.db.query(OTP).filter(
            OTP.user_id == user_id
        ).order_by(OTP.id.desc()).first()

    def mark_as_used(self, otp: OTP) -> OTP:
        otp.otp_used = True
        self.db.commit()
        self.db.refresh(otp)
        return otp

    def invalidate_user_otps(self, user_id: int) -> None:
        """Mark all unused OTPs for a user as used"""
        self.db.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.otp_used == False
        ).update({OTP.otp_used: True})
        self.db.commit()

    def cleanup_expired_otps(self) -> None:
        """Remove expired OTPs from database"""
        current_time = int(time.time())
        self.db.query(OTP).filter(OTP.expired_time < current_time).delete()
        self.db.commit()