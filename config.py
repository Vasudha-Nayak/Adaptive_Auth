"""
Central configuration.
Edit DB_PASSWORD (and DB_USER/DB_HOST if needed) to match your local MySQL setup.
"""

# ---- MySQL connection settings ----
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root1234"      # <-- put your MySQL root/user password here
DB_NAME = "adaptive_auth"

# ---- Flask ----
SECRET_KEY = "dev-secret-key-change-this-in-production-123456"

# ---- Policy constants (tweak as needed) ----
ALLOWED_EMAIL_DOMAIN = "company.com"   # emails must be like xyz@company.com

MAX_PASSWORD_ATTEMPTS = 5              # total attempts before lock
ADAPTIVE_TRIGGER_AFTER = 3             # after this many fails, OTP is also required in step 1

MAX_OTP_RESENDS = 2                    # 2 resends allowed, 3rd resend -> lock

MAX_PATTERN_ATTEMPTS = 2               # 2 attempts allowed for the pattern step

PATTERN_MIN_LEN = 4
PATTERN_MAX_LEN = 6
