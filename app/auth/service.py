from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, Tuple
import bcrypt
import jwt
import time
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config
from pathlib import Path

from app.auth.repository import OTPRepository
from app.auth.entity import OTP
from app.auth.schema import RegisterSchema, RequestVerifySchema, VerifySchema, LoginSchema, RecoverPasswordSchema
from app.users.repository import UserRepository
from app.users.entity import User

class AuthService:
    def __init__(self, db: Session):
        self.otp_repo = OTPRepository(db)
        self.user_repo = UserRepository(db)
        self.jwt_secret = Config.JWT_SECRET
        self.jwt_algorithm = "HS256"
        self.jwt_expiration = 3600 * 24  # 24 hours
        self.otp_expiration = 300  # 5 minutes

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def _generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))

    def _generate_new_password(self) -> str:
        """Generate 8-character password with uppercase, lowercase, and digits"""
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        
        # Ensure at least one character from each type
        password = [
            random.choice(uppercase),
            random.choice(lowercase),
            random.choice(digits)
        ]
        
        # Fill remaining 5 characters with random mix
        all_chars = uppercase + lowercase + digits
        for _ in range(5):
            password.append(random.choice(all_chars))
        
        # Shuffle to avoid predictable pattern
        random.shuffle(password)
        return ''.join(password)

    def _send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Send email (implement based on your email service)"""
        try:
            # Configure your email settings
            smtp_server = Config.SMTP_SERVER
            smtp_port = Config.SMTP_PORT
            smtp_username = Config.SMTP_USERNAME
            smtp_password = Config.SMTP_PASSWORD
            
            if not smtp_username or not smtp_password:
                print("Email credentials not configured")
                return False

            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach body with appropriate content type
            content_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, content_type))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def _generate_jwt_token(self, user: User) -> str:
        """Generate JWT token for user"""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "exp": int(time.time()) + self.jwt_expiration
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Ensure token is a string (decode if it's bytes)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        return token

    def register(self, data: RegisterSchema) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
        """Register a new user"""
        # Check if username already exists
        if self.user_repo.get_by_username(data.username):
            return None, {"error": "Username already exists"}
            
        # Check if email already exists
        if self.user_repo.get_by_email(data.email):
            return None, {"error": "Email already exists"}
            
        # Check if phonenumber already exists
        if data.phonenumber and self.user_repo.get_by_phonenumber(data.phonenumber):
            return None, {"error": "Phone number already exists"}

        # Hash password
        hashed_password = self._hash_password(data.password)
        
        # Create user
        user = User(
            username=data.username,
            email=data.email,
            phonenumber=data.phonenumber,
            password=hashed_password,
            is_verified=False,
            role="user"
        )
        
        created_user = self.user_repo.create(user)
        
        # Send verification OTP
        otp_sent = self._send_verification_otp(created_user)
        
        return {
            "message": "User registered successfully. Please check your email for verification code.",
            "user_id": created_user.id,
            "otp_sent": otp_sent
        }, None

    def _send_verification_otp(self, user: User) -> bool:
        """Generate and send OTP to user's email"""
        # Invalidate existing OTPs
        self.otp_repo.invalidate_user_otps(user.id)
        
        # Generate new OTP
        otp_code = self._generate_otp()
        expired_time = int(time.time()) + self.otp_expiration
        
        # Save OTP to database
        otp = OTP(
            user_id=user.id,
            otp_code=otp_code,
            expired_time=expired_time
        )
        self.otp_repo.create(otp)
        
        # Load HTML template
        template_path = Path(__file__).parent / "templates" / "otp.html"
        
        with open(template_path, 'r', encoding='utf-8') as file:
            html_body = file.read()
        
        # Replace placeholders
        html_body = html_body.replace("{{ username }}", user.username)
        html_body = html_body.replace("{{ otp }}", otp_code)
        
        # Send email
        subject = "Verify Your Account"
        
        return self._send_email(user.email, subject, html_body, is_html=True)

    def _send_password_recovery_email(self, user: User, new_password: str) -> bool:
        """Send password recovery email with new password"""
        # Load HTML template
        template_path = Path(__file__).parent / "templates" / "password_recovery.html"
        
        with open(template_path, 'r', encoding='utf-8') as file:
            html_body = file.read()
        
        # Replace placeholders
        html_body = html_body.replace("{{ username }}", user.username)
        html_body = html_body.replace("{{ newPassword }}", new_password)
        
        # Send email
        subject = "Password Recovery - Heartify"
        
        return self._send_email(user.email, subject, html_body, is_html=True)

    def request_verify(self, data: RequestVerifySchema) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
        """Send verification OTP to user's email"""
        user = self.user_repo.get_by_email(data.email)
        if not user:
            return None, {"error": "User not found"}
            
        if user.is_verified:
            return None, {"error": "User is already verified"}
        
        otp_sent = self._send_verification_otp(user)
        
        return {
            "message": "Verification code sent to your email",
            "otp_sent": otp_sent
        }, None

    def verify(self, data: VerifySchema) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
        """Verify user account with OTP"""
        user = self.user_repo.get_by_email(data.email)
        if not user:
            return None, {"error": "User not found"}
            
        if user.is_verified:
            return None, {"error": "User is already verified"}
        
        # Check OTP
        otp = self.otp_repo.get_by_user_and_code(user.id, data.otp_code)
        if not otp:
            return None, {"error": "Invalid or expired OTP"}
        
        # Mark OTP as used
        self.otp_repo.mark_as_used(otp)
        
        # Mark user as verified
        user.is_verified = True
        self.user_repo.update(user)
        
        return {"message": "Account verified successfully"}, None

    def login(self, data: LoginSchema) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
        """Login user and return JWT token"""
        user = self.user_repo.get_by_username(data.username)
        if not user:
            return None, {"error": "Invalid username or password"}
        
        # Check password
        if not self._verify_password(data.password, user.password):
            return None, {"error": "Invalid username or password"}
        
        # Check if user is verified
        if not user.is_verified:
            return None, {"error": "Please verify your account before logging in"}
        
        # Generate JWT token
        access_token = self._generate_jwt_token(user)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phonenumber": user.phonenumber,
                "role": user.role,
                "is_verified": user.is_verified
            }
        }, None

    def recover_password(self, data: RecoverPasswordSchema) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
        """Recover password by validating username, email, and phone number"""
        # Step 1: Check if username exists
        user = self.user_repo.get_by_username(data.username)
        if not user:
            return None, {"error": "Username not found"}
        
        # Step 2: Check if email matches
        if user.email != data.email:
            return None, {"error": "Email does not match"}
        
        # Step 3: Check if phone number matches
        if user.phonenumber != data.phone_number:
            return None, {"error": "Phone number does not match"}
        
        # All validations passed, generate new password
        new_password = self._generate_new_password()
        
        # Hash and update password
        hashed_password = self._hash_password(new_password)
        user.password = hashed_password
        self.user_repo.update(user)
        
        # Send recovery email
        email_sent = self._send_password_recovery_email(user, new_password)
        
        return {
            "message": "Password reset successfully. Please check your email for the new password.",
            "email_sent": email_sent
        }, None

    def verify_jwt_token(self, token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"