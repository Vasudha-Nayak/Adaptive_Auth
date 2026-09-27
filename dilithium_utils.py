"""
Objective 2 — Post-quantum digital signature layer.

Uses CRYSTALS-Dilithium (ML-DSA), NIST security level 3, via the pure-Python
'dilithium-py' library (no C compiler needed).

This module is purely additive: it does not modify any existing registration
or login logic. It only signs the session key that is already generated at
the end of a successful login (Step 3), so that its authenticity can be
verified later — protecting it against future quantum-capable attackers.
"""
import os
from dilithium_py.dilithium import Dilithium3

ALGO_NAME = "Dilithium3"

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_DIR = os.path.join(_THIS_DIR, "keys")
PUBLIC_KEY_PATH = os.path.join(KEY_DIR, "dilithium_public.key")
PRIVATE_KEY_PATH = os.path.join(KEY_DIR, "dilithium_private.key")


def _ensure_keypair():
    """
    Generate a server-wide Dilithium3 keypair once, and persist it to disk so
    the SAME keys are reused across app restarts. (If a new keypair were
    generated every restart, signatures created before the restart would no
    longer verify.)
    """
    os.makedirs(KEY_DIR, exist_ok=True)

    if os.path.exists(PUBLIC_KEY_PATH) and os.path.exists(PRIVATE_KEY_PATH):
        with open(PUBLIC_KEY_PATH, "rb") as f:
            pk = f.read()
        with open(PRIVATE_KEY_PATH, "rb") as f:
            sk = f.read()
        return pk, sk

    pk, sk = Dilithium3.keygen()
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(pk)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(sk)
    return pk, sk


PUBLIC_KEY, PRIVATE_KEY = _ensure_keypair()


def sign_session_key(session_key: str) -> str:
    """Sign a session key string with the server's Dilithium3 private key.
    Returns the signature encoded as a hex string (safe to store in MySQL as TEXT)."""
    sig_bytes = Dilithium3.sign(PRIVATE_KEY, session_key.encode("utf-8"))
    return sig_bytes.hex()


def verify_session_key(session_key: str, signature_hex: str) -> bool:
    """Verify a session key against its signature using the server's public key."""
    try:
        sig_bytes = bytes.fromhex(signature_hex)
    except (ValueError, TypeError):
        return False
    return Dilithium3.verify(PUBLIC_KEY, session_key.encode("utf-8"), sig_bytes)
