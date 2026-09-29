"""
Utility functions: password hashing, validation rules, OTP generation,
and session key generation.

NOTE: the old 3x3 pattern generator/hasher has been removed — Step 3 of
login is now a face-biometric check (see face_utils.py), not a shared
secret, so there is nothing here to generate or hash for it.
"""
import re
import random
import secrets
import bcrypt
import config


# ---------------- Hashing ----------------

def hash_value(value: str) -> str:
    """bcrypt-hash any string (used for passwords)."""
    return bcrypt.hashpw(value.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_value(value: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(value.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------- Validation ----------------

def is_valid_password(password: str) -> bool:
    """At least 8 chars, one uppercase letter, one digit."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True


def is_valid_email(email: str) -> bool:
    """Must look like xyz@company.com (domain configurable in config.py)."""
    pattern = r"^[a-zA-Z0-9_.+-]+@" + re.escape(config.ALLOWED_EMAIL_DOMAIN) + r"$"
    return bool(re.match(pattern, email))


# ---------------- OTP ----------------

def generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


# ---------------- Session key ----------------

def generate_session_key() -> str:
    """Fresh random session key generated on every successful login."""
    return secrets.token_hex(32)


# ---------------- Misc ----------------

def generate_challenge_token() -> str:
    """Single-use per-attempt token for the face-verify step, to make a bare
    replay of a previous request a little harder (see face_utils.py)."""
    return secrets.token_urlsafe(24)
