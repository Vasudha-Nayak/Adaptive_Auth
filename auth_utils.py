"""
Utility functions: password/pattern hashing, validation rules, OTP + pattern generation,
and session key generation.
"""
import re
import random
import secrets
import bcrypt
import config


# ---------------- Hashing ----------------

def hash_value(value: str) -> str:
    """bcrypt-hash any string (used for both passwords and patterns)."""
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


# ---------------- Pattern (3x3 grid, dots numbered 1-9) ----------------

def generate_pattern() -> str:
    """Returns a comma-separated sequence, e.g. '2,5,8,9'."""
    length = random.randint(config.PATTERN_MIN_LEN, config.PATTERN_MAX_LEN)
    dots = random.sample(range(1, 10), length)
    return ",".join(str(d) for d in dots)


# ---------------- Session key ----------------

def generate_session_key() -> str:
    """Fresh random session key generated on every successful login."""
    return secrets.token_hex(32)
