import secrets
import pyotp
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def generate_session_key() -> str:
    return secrets.token_hex(32)

def generate_otp() -> str:
    return pyotp.TOTP(pyotp.random_base32(), interval=120).now()

def otp_expiry_time(minutes: int = 2) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)

def is_otp_valid(stored_otp: str, submitted_otp: str, expiry: datetime) -> bool:
    if not stored_otp or not expiry:
        return False
    if datetime.utcnow() > expiry:
        return False
    return stored_otp == submitted_otp