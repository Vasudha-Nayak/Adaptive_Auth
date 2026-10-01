"""
crypto_adapter.py
-----------------
Post-quantum cryptography adapter for Objective 3 evaluation.

Backend priority:
1. dilithium_py
2. pqcrypto
3. liboqs

The adapter automatically detects which supported backend is available.

IMPORTANT:
- This file is ONLY for the evaluation/benchmarking folder.
- Do NOT modify your main project's dilithium_utils.py.
"""

from __future__ import annotations

import os
import time
from typing import Tuple, Optional


# ============================================================
# Backend detection
# ============================================================

BACKEND = None

Dilithium3 = None
ml_dsa_65 = None
oqs = None


# ------------------------------------------------------------
# 1. Try dilithium-py
# ------------------------------------------------------------

try:
    from dilithium_py.dilithium3 import Dilithium3

    BACKEND = "dilithium_py"

except Exception:
    Dilithium3 = None


# ------------------------------------------------------------
# 2. Try pqcrypto
# ------------------------------------------------------------

if BACKEND is None:
    try:
        from pqcrypto.sign import ml_dsa_65

        BACKEND = "pqcrypto"

    except Exception:
        ml_dsa_65 = None


# ------------------------------------------------------------
# 3. Try liboqs
# ------------------------------------------------------------

if BACKEND is None:
    try:
        import oqs

        BACKEND = "liboqs"

    except Exception:
        oqs = None


# ------------------------------------------------------------
# Fail if nothing is available
# ------------------------------------------------------------

if BACKEND is None:
    raise RuntimeError(
        "\nNo supported post-quantum cryptography backend was found.\n\n"
        "Install one of the following:\n"
        "  pip install dilithium-py\n"
        "or\n"
        "  pip install pqcrypto\n"
        "or configure liboqs-python correctly.\n"
    )


print(f"[crypto_adapter] Using backend: {BACKEND}")


# ============================================================
# Backend information
# ============================================================

def backend_name() -> str:
    """
    Return the name of the active PQ cryptography backend.
    """
    return BACKEND


# ============================================================
# Key generation
# ============================================================

def keygen() -> Tuple[bytes, bytes]:
    """
    Generate a post-quantum signing key pair.

    Returns:
        public_key, secret_key
    """

    # --------------------------------------------------------
    # dilithium-py
    # --------------------------------------------------------

    if BACKEND == "dilithium_py":

        public_key, secret_key = Dilithium3.keygen()

        return public_key, secret_key


    # --------------------------------------------------------
    # pqcrypto
    #
    # IMPORTANT:
    # Your installed version uses:
    #     ml_dsa_65.keygen()
    #
    # NOT:
    #     ml_dsa_65.generate_keypair()
    # --------------------------------------------------------

    if BACKEND == "pqcrypto":

        public_key, secret_key = ml_dsa_65.keygen()

        return public_key, secret_key


    # --------------------------------------------------------
    # liboqs
    # --------------------------------------------------------

    if BACKEND == "liboqs":

        signer = oqs.Signature("ML-DSA-65")

        public_key, secret_key = signer.generate_keypair()

        return public_key, secret_key


    raise RuntimeError(
        f"Unsupported cryptography backend: {BACKEND}"
    )


# ============================================================
# Signing
# ============================================================

def sign(secret_key: bytes, message: bytes) -> bytes:
    """
    Sign a message using the post-quantum signature scheme.

    Args:
        secret_key: secret/private signing key
        message: message to sign

    Returns:
        signature bytes
    """

    # --------------------------------------------------------
    # dilithium-py
    # --------------------------------------------------------

    if BACKEND == "dilithium_py":

        return Dilithium3.sign(
            secret_key,
            message
        )


    # --------------------------------------------------------
    # pqcrypto
    # --------------------------------------------------------

    if BACKEND == "pqcrypto":

        return ml_dsa_65.sign(
            secret_key,
            message
        )


    # --------------------------------------------------------
    # liboqs
    # --------------------------------------------------------

    if BACKEND == "liboqs":

        signer = oqs.Signature("ML-DSA-65")

        return signer.sign(
            message,
            secret_key
        )


    raise RuntimeError(
        f"Unsupported cryptography backend: {BACKEND}"
    )


# ============================================================
# Verification
# ============================================================

def verify(
    public_key: bytes,
    message: bytes,
    signature: bytes
) -> bool:
    """
    Verify a post-quantum digital signature.

    Returns:
        True  -> signature valid
        False -> signature invalid
    """

    # --------------------------------------------------------
    # dilithium-py
    # --------------------------------------------------------

    if BACKEND == "dilithium_py":

        try:
            return bool(
                Dilithium3.verify(
                    public_key,
                    message,
                    signature
                )
            )

        except Exception:
            return False


    # --------------------------------------------------------
    # pqcrypto
    #
    # pqcrypto.verify() returns normally when valid and raises
    # an exception when verification fails.
    # --------------------------------------------------------

    if BACKEND == "pqcrypto":

        try:

            ml_dsa_65.verify(
                public_key,
                message,
                signature
            )

            return True

        except Exception:

            return False


    # --------------------------------------------------------
    # liboqs
    # --------------------------------------------------------

    if BACKEND == "liboqs":

        try:

            signer = oqs.Signature("ML-DSA-65")

            return bool(
                signer.verify(
                    message,
                    signature,
                    public_key
                )
            )

        except Exception:

            return False


    raise RuntimeError(
        f"Unsupported cryptography backend: {BACKEND}"
    )


# ============================================================
# Size information
# ============================================================

def get_sizes() -> dict:
    """
    Return public key, secret key and signature sizes.

    Sizes are obtained from the installed backend whenever
    possible.
    """

    # --------------------------------------------------------
    # pqcrypto
    # --------------------------------------------------------

    if BACKEND == "pqcrypto":

        return {
            "public_key_bytes": int(
                ml_dsa_65.PUBLIC_KEY_SIZE
            ),
            "secret_key_bytes": int(
                ml_dsa_65.SECRET_KEY_SIZE
            ),
            "signature_bytes": int(
                ml_dsa_65.SIGNATURE_SIZE
            )
        }


    # --------------------------------------------------------
    # dilithium-py
    #
    # Measure actual generated objects.
    # --------------------------------------------------------

    if BACKEND == "dilithium_py":

        public_key, secret_key = keygen()

        message = b"size measurement message"

        signature = sign(
            secret_key,
            message
        )

        return {
            "public_key_bytes": len(public_key),
            "secret_key_bytes": len(secret_key),
            "signature_bytes": len(signature)
        }


    # --------------------------------------------------------
    # liboqs
    # --------------------------------------------------------

    if BACKEND == "liboqs":

        signer = oqs.Signature("ML-DSA-65")

        public_key, secret_key = signer.generate_keypair()

        signature = signer.sign(
            b"size measurement message",
            secret_key
        )

        return {
            "public_key_bytes": len(public_key),
            "secret_key_bytes": len(secret_key),
            "signature_bytes": len(signature)
        }


    raise RuntimeError(
        f"Unsupported cryptography backend: {BACKEND}"
    )


# ============================================================
# Benchmark key generation
# ============================================================

def benchmark_keygen(
    iterations: int = 10
) -> dict:
    """
    Benchmark PQ key generation.

    Returns timing statistics in seconds and milliseconds.
    """

    times = []

    for _ in range(iterations):

        start = time.perf_counter()

        keygen()

        elapsed = time.perf_counter() - start

        times.append(elapsed)


    return _timing_statistics(times)


# ============================================================
# Benchmark signing
# ============================================================

def benchmark_sign(
    iterations: int = 100
) -> dict:
    """
    Benchmark PQ signature generation.
    """

    public_key, secret_key = keygen()

    message = (
        b"Adaptive authentication session challenge "
        b"for Objective 3 benchmark"
    )

    times = []

    for _ in range(iterations):

        start = time.perf_counter()

        sign(
            secret_key,
            message
        )

        elapsed = time.perf_counter() - start

        times.append(elapsed)


    return _timing_statistics(times)


# ============================================================
# Benchmark verification
# ============================================================

def benchmark_verify(
    iterations: int = 100
) -> dict:
    """
    Benchmark PQ signature verification.
    """

    public_key, secret_key = keygen()

    message = (
        b"Adaptive authentication session challenge "
        b"for Objective 3 benchmark"
    )

    signature = sign(
        secret_key,
        message
    )

    times = []

    for _ in range(iterations):

        start = time.perf_counter()

        verify(
            public_key,
            message,
            signature
        )

        elapsed = time.perf_counter() - start

        times.append(elapsed)


    return _timing_statistics(times)


# ============================================================
# Timing statistics
# ============================================================

def _timing_statistics(times: list) -> dict:
    """
    Calculate basic timing statistics.

    Input:
        times -> list of seconds

    Returns:
        mean, median, min, max, standard deviation,
        p95 in seconds and milliseconds.
    """

    if not times:

        return {
            "n": 0,
            "mean_s": 0.0,
            "median_s": 0.0,
            "min_s": 0.0,
            "max_s": 0.0,
            "std_s": 0.0,
            "p95_s": 0.0,
            "mean_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0
        }


    import statistics

    sorted_times = sorted(times)

    n = len(sorted_times)

    mean_s = statistics.mean(sorted_times)

    median_s = statistics.median(sorted_times)

    min_s = min(sorted_times)

    max_s = max(sorted_times)

    if n >= 2:
        std_s = statistics.stdev(sorted_times)
    else:
        std_s = 0.0


    # Simple nearest-rank p95
    index = max(
        0,
        min(
            n - 1,
            int(0.95 * n) - 1
        )
    )

    p95_s = sorted_times[index]


    return {
        "n": n,

        "mean_s": mean_s,
        "median_s": median_s,

        "min_s": min_s,
        "max_s": max_s,

        "std_s": std_s,

        "p95_s": p95_s,

        "mean_ms": mean_s * 1000,
        "median_ms": median_s * 1000,
        "p95_ms": p95_s * 1000
    }


# ============================================================
# Integrity test
# ============================================================

def integrity_test() -> dict:
    """
    Run basic cryptographic integrity tests.

    Tests:
        1. Correct signature verifies.
        2. Modified message fails.
        3. Modified signature fails.
        4. Wrong public key fails.

    This is useful for Objective 3 security evaluation.
    """

    message = (
        b"Adaptive authentication session "
        b"verification challenge"
    )

    # --------------------------------------------------------
    # Generate keys
    # --------------------------------------------------------

    start = time.perf_counter()

    public_key, secret_key = keygen()

    keygen_time = (
        time.perf_counter() - start
    )


    # --------------------------------------------------------
    # Sign
    # --------------------------------------------------------

    start = time.perf_counter()

    signature = sign(
        secret_key,
        message
    )

    sign_time = (
        time.perf_counter() - start
    )


    # --------------------------------------------------------
    # Correct verification
    # --------------------------------------------------------

    start = time.perf_counter()

    valid_result = verify(
        public_key,
        message,
        signature
    )

    verify_time = (
        time.perf_counter() - start
    )


    # --------------------------------------------------------
    # Modified message
    # --------------------------------------------------------

    modified_message = (
        b"Modified adaptive authentication challenge"
    )

    modified_message_result = verify(
        public_key,
        modified_message,
        signature
    )


    # --------------------------------------------------------
    # Modified signature
    # --------------------------------------------------------

    modified_signature = bytearray(signature)

    if len(modified_signature) > 0:

        modified_signature[0] ^= 0x01

    modified_signature = bytes(
        modified_signature
    )

    modified_signature_result = verify(
        public_key,
        message,
        modified_signature
    )


    # --------------------------------------------------------
    # Wrong public key
    # --------------------------------------------------------

    wrong_public_key, _ = keygen()

    wrong_key_result = verify(
        wrong_public_key,
        message,
        signature
    )


    # --------------------------------------------------------
    # Sizes
    # --------------------------------------------------------

    sizes = get_sizes()


    return {

        "backend": BACKEND,

        "valid_signature": bool(
            valid_result
        ),

        "modified_message_rejected": not bool(
            modified_message_result
        ),

        "modified_signature_rejected": not bool(
            modified_signature_result
        ),

        "wrong_public_key_rejected": not bool(
            wrong_key_result
        ),

        "keygen_time_s": keygen_time,

        "sign_time_s": sign_time,

        "verify_time_s": verify_time,

        "keygen_time_ms": keygen_time * 1000,

        "sign_time_ms": sign_time * 1000,

        "verify_time_ms": verify_time * 1000,

        **sizes
    }


# ============================================================
# Session-key uniqueness test
# ============================================================

def session_key_uniqueness(
    n: int = 10000,
    key_bytes: int = 32
) -> dict:
    """
    Generate random session keys and check for duplicates.

    This directly evaluates whether fresh session keys are
    unique across logins.

    This is NOT a proof of cryptographic security; it is an
    empirical uniqueness test.
    """

    keys = set()

    duplicate_count = 0


    for _ in range(n):

        key = os.urandom(key_bytes)

        if key in keys:

            duplicate_count += 1

        else:

            keys.add(key)


    unique_count = len(keys)


    if n > 0:

        uniqueness_pct = (
            unique_count / n
        ) * 100

    else:

        uniqueness_pct = 0.0


    return {

        "requested_keys": n,

        "unique_keys": unique_count,

        "duplicate_keys": duplicate_count,

        "uniqueness_pct": uniqueness_pct,

        "key_size_bytes": key_bytes
    }


# ============================================================
# Full crypto benchmark
# ============================================================

def run_crypto_benchmark(
    keygen_iterations: int = 10,
    sign_iterations: int = 100,
    verify_iterations: int = 100,
    session_keys: int = 10000
) -> dict:
    """
    Run the complete PQ cryptography benchmark.
    """

    print("\n" + "=" * 60)

    print("POST-QUANTUM CRYPTOGRAPHY BENCHMARK")

    print("=" * 60)

    print(
        f"Backend: {BACKEND}"
    )


    print(
        "\n[1/4] Key generation benchmark..."
    )

    keygen_results = benchmark_keygen(
        keygen_iterations
    )


    print(
        "[2/4] Signature benchmark..."
    )

    sign_results = benchmark_sign(
        sign_iterations
    )


    print(
        "[3/4] Verification benchmark..."
    )

    verify_results = benchmark_verify(
        verify_iterations
    )


    print(
        "[4/4] Session-key uniqueness..."
    )

    uniqueness_results = session_key_uniqueness(
        session_keys
    )


    integrity_results = integrity_test()


    return {

        "backend": BACKEND,

        "keygen": keygen_results,

        "sign": sign_results,

        "verify": verify_results,

        "integrity": integrity_results,

        "session_keys": uniqueness_results,

        "sizes": get_sizes()
    }


# ============================================================
# Command-line execution
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)

    print(" CRYPTO ADAPTER TEST")

    print("=" * 60)

    print(
        f"\nDetected backend: {BACKEND}"
    )


    print(
        "\nRunning integrity test..."
    )


    try:

        result = integrity_test()


        print("\nIntegrity test results:")

        print(
            f"  Backend: "
            f"{result['backend']}"
        )

        print(
            f"  Valid signature: "
            f"{result['valid_signature']}"
        )

        print(
            f"  Modified message rejected: "
            f"{result['modified_message_rejected']}"
        )

        print(
            f"  Modified signature rejected: "
            f"{result['modified_signature_rejected']}"
        )

        print(
            f"  Wrong public key rejected: "
            f"{result['wrong_public_key_rejected']}"
        )


        print("\nCryptographic sizes:")

        print(
            f"  Public key: "
            f"{result['public_key_bytes']} bytes"
        )

        print(
            f"  Secret key: "
            f"{result['secret_key_bytes']} bytes"
        )

        print(
            f"  Signature: "
            f"{result['signature_bytes']} bytes"
        )


        print("\nOperation times:")

        print(
            f"  Key generation: "
            f"{result['keygen_time_ms']:.3f} ms"
        )

        print(
            f"  Signing: "
            f"{result['sign_time_ms']:.3f} ms"
        )

        print(
            f"  Verification: "
            f"{result['verify_time_ms']:.3f} ms"
        )


        print(
            "\n✓ Crypto adapter is working correctly."
        )


    except Exception as e:

        print(
            "\n✗ Crypto adapter test failed."
        )

        print(
            f"\nError: {type(e).__name__}: {e}"
        )

        raise