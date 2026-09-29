"""
Central configuration.
Edit DB_PASSWORD (and DB_USER/DB_HOST if needed) to match your local MySQL setup.
"""
import os

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

# ---- Face biometric step (Objective 1, Step 3 — replaces the old 3x3 pattern) ----
MAX_FACE_ATTEMPTS = 2                  # 2 failed face-scans allowed, 3rd -> lock (same as old pattern rule)

# Minimum confidence (0-1) the "Face" class must reach, AND must beat "Not Face" by,
# for a login attempt to be accepted. Raise this for stricter matching.
FACE_MATCH_THRESHOLD = 0.75

# The exact class labels used when training every user's personal Teachable
# Machine model. Must match static/js/face_register.js exactly.
FACE_CLASS_LABEL = "Face"
NOT_FACE_CLASS_LABEL = "Not Face"

# Where each user's trained model files (model.json / weights.bin / metadata.json)
# are stored on disk, keyed by user id. NOT served from /static — served through
# an access-gated Flask route (see app.py: /face-model/<user_id>/<filename>) so a
# visitor can't casually enumerate/download every user's model.
FACE_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "face_models")
FACE_MODEL_FILENAMES = ("model.json", "weights.bin", "metadata.json")
