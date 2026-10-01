"""
eval_config.py
--------------
Central configuration file for Objective 3 evaluation.

Change values here instead of modifying the benchmark files.
"""

from pathlib import Path


# ============================================================
# GENERAL SETTINGS
# ============================================================

SEED = 42

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# PERFORMANCE BENCHMARK SETTINGS
# ============================================================

# Number of benchmark iterations
N_ITER = 200

# Number of password-specific measurements
N_ITER_PW = 40

# Warm-up iterations before measurement
N_WARMUP = 10

# Number of memory measurements
N_MEM = 20


# ============================================================
# PASSWORD SETTINGS
# ============================================================

# Same hashing method used by Flask/Werkzeug
PASSWORD_HASH_METHOD = "pbkdf2:sha256"


# ============================================================
# POST-QUANTUM CRYPTOGRAPHY SETTINGS
# ============================================================

# Set True ONLY if your application generates a new
# Dilithium key pair for every login.
#
# If your current application already has a registered
# key pair and only signs during login, keep this False.
KEYGEN_PER_LOGIN = False

# Dilithium / ML-DSA security level
DILITHIUM_LEVEL = 3


# ============================================================
# OTP SETTINGS
# ============================================================

OTP_DIGITS = 6

# Maximum verification attempts for one OTP
OTP_TRIES_PER_CODE = 3

# Maximum number of OTP codes
MAX_OTP_CODES = 3


# ============================================================
# FACE AUTHENTICATION SETTINGS
# ============================================================

# Maximum face verification attempts
MAX_FACE_TRIES = 2

# Minimum confidence required for accepting a face
FACE_THRESHOLD = 0.90


# Approximate model size.
#
# Replace these with the actual sizes of your
# Teachable Machine model files when available.
FACE_MODEL_BYTES = {
    "model_json": 0,
    "weights_bin": 0,
    "metadata_json": 0
}


# ============================================================
# HUMAN / CLIENT / NETWORK ASSUMPTIONS
# ============================================================
#
# These values are MODELLED assumptions.
# They are NOT server measurements.
#
# If you obtain real measurements, replace these values.

HUMAN_S = {
    "password": 6.0,
    "otp": 15.0,
    "face": 3.0
}


CLIENT_FACE_S = {
    # Time required to load the Teachable Machine model
    "model_load": 1.2,

    # Time for one face prediction
    "predict": 0.15
}


# Network round-trip time assumption
NET_RTT_S = 0.05


# ============================================================
# SECURITY MODEL SETTINGS
# ============================================================

# Password popularity distribution parameter
ZIPF_S = 0.7

# Size of hypothetical password vocabulary
VOCAB = 1_000_000

# Number of users in modeled attack scenario
N_USERS = 200_000

# Total attacker attempts
ATTEMPT_BUDGET = 10_000


# Probability that an attacker can access
# a user's OTP mailbox.
#
# This is a modeled assumption.
P_MAILBOX = 0.05


# Default face False Acceptance Rate.
#
# IMPORTANT:
# Replace this with experimentally measured FAR
# when actual face score data is available.
FAR_DEFAULT = 0.02


# ============================================================
# SECURITY TEST SETTINGS
# ============================================================

# Number of tampering attempts
N_TAMPER = 200

# Number of session keys used for uniqueness test
N_SESSION_KEYS = 10000


# ============================================================
# OUTPUT SETTINGS
# ============================================================

SAVE_CSV = True
SAVE_PNG = True

# DPI for journal-quality figures
FIGURE_DPI = 300


# ============================================================
# QUICK MODE
# ============================================================

QUICK_N_ITER = 30
QUICK_N_ITER_PW = 10
QUICK_N_MEM = 5
QUICK_N_TAMPER = 30
QUICK_N_SESSION_KEYS = 1000


def get_iterations(quick=False):
    """
    Return benchmark iteration values depending on
    whether quick mode is enabled.
    """

    if quick:
        return {
            "n_iter": QUICK_N_ITER,
            "n_iter_pw": QUICK_N_ITER_PW,
            "n_mem": QUICK_N_MEM,
            "n_tamper": QUICK_N_TAMPER,
            "n_session_keys": QUICK_N_SESSION_KEYS
        }

    return {
        "n_iter": N_ITER,
        "n_iter_pw": N_ITER_PW,
        "n_mem": N_MEM,
        "n_tamper": N_TAMPER,
        "n_session_keys": N_SESSION_KEYS
    }