"""
bench_performance.py
--------------------
Objective 3 - Performance Evaluation

Measures:
    - Password verification latency
    - OTP processing latency
    - Face authentication server-side latency
    - Session-key generation latency
    - PQ signature latency
    - Static vs Adaptive login time
    - CPU usage
    - Memory usage
    - Latency distribution

All measured values are local experimental measurements.
Human interaction and network delay are treated separately
as configurable assumptions in eval_config.py.
"""

import hashlib
import os
import random
import statistics
import time
import tracemalloc

import psutil
from werkzeug.security import generate_password_hash, check_password_hash

import eval_config
import crypto_adapter


# ============================================================
# HELPERS
# ============================================================

def mean(values):
    return statistics.mean(values) if values else 0.0


def median(values):
    return statistics.median(values) if values else 0.0


def stdev(values):
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def percentile(values, p):
    if not values:
        return 0.0

    values = sorted(values)

    index = (len(values) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)

    fraction = index - lower

    return (
        values[lower]
        + (values[upper] - values[lower]) * fraction
    )


def measure(function, iterations):
    """
    Measure execution time of a function.
    Returns milliseconds.
    """

    # Warm-up
    for _ in range(eval_config.N_WARMUP):
        function()

    values = []

    for _ in range(iterations):

        start = time.perf_counter()

        function()

        elapsed = time.perf_counter() - start

        values.append(elapsed * 1000)

    return values


# ============================================================
# PASSWORD VERIFICATION
# ============================================================

def password_setup():
    """
    Create one password hash for benchmarking.
    """

    password = "JournalTestPassword123!"

    password_hash = generate_password_hash(
        password,
        method=eval_config.PASSWORD_HASH_METHOD
    )

    return password, password_hash


def benchmark_password(iterations):
    password, password_hash = password_setup()

    def verify():
        check_password_hash(
            password_hash,
            password
        )

    return measure(
        verify,
        iterations
    )


# ============================================================
# OTP
# ============================================================

def generate_otp():
    """
    Generate a six-digit OTP.
    """

    return str(
        random.randint(
            10 ** (eval_config.OTP_DIGITS - 1),
            10 ** eval_config.OTP_DIGITS - 1
        )
    )


def benchmark_otp(iterations):
    """
    Measures local OTP generation + comparison.
    """

    otp = generate_otp()

    def verify():

        entered = otp

        return entered == otp

    return measure(
        verify,
        iterations
    )


# ============================================================
# FACE SERVER PROCESSING
# ============================================================

def benchmark_face_server(iterations):
    """
    Measures lightweight server-side face authentication
    processing.

    NOTE:
    This does NOT measure the browser's Teachable Machine
    inference time.

    Actual browser inference should be measured separately
    using performance.now() in face_login.js.
    """

    score = 0.95
    threshold = eval_config.FACE_THRESHOLD

    def verify():

        return score >= threshold

    return measure(
        verify,
        iterations
    )


# ============================================================
# SESSION KEY GENERATION
# ============================================================

def generate_session_key():
    """
    Generate a fresh 256-bit session key.
    """

    return os.urandom(32)


def benchmark_session_key(iterations):

    return measure(
        generate_session_key,
        iterations
    )


# ============================================================
# PQ SIGNATURE
# ============================================================

def benchmark_signature(n):
    """
    Benchmark ML-DSA-65 signature generation.

    Uses the exact key format returned by the installed
    pqcrypto.sign.ml_dsa_65.keygen() API.
    """

    public_key, secret_key = crypto_adapter.keygen()

    message = b"Adaptive authentication session key"

    def sign_message():
        crypto_adapter.sign(
            secret_key,
            message
        )

    return measure(
        sign_message,
        n
    )


def benchmark_signature_verification(n):
    """
    Benchmark ML-DSA-65 signature verification.
    """

    public_key, secret_key = crypto_adapter.keygen()

    message = b"Adaptive authentication session key"

    signature = crypto_adapter.sign(
        secret_key,
        message
    )

    def verify_message():
        crypto_adapter.verify(
            public_key,
            message,
            signature
        )

    return measure(
        verify_message,
        n
    )


# ============================================================
# CPU MEASUREMENT
# ============================================================

def measure_cpu(function):

    process = psutil.Process()

    process.cpu_percent(None)

    start = time.perf_counter()

    function()

    elapsed = time.perf_counter() - start

    cpu = process.cpu_percent(None)

    return {
        "elapsed_ms": elapsed * 1000,
        "cpu_percent": cpu
    }


# ============================================================
# MEMORY MEASUREMENT
# ============================================================

def measure_memory(function):

    tracemalloc.start()

    function()

    current, peak = tracemalloc.get_traced_memory()

    tracemalloc.stop()

    return {
        "current_kb": current / 1024,
        "peak_kb": peak / 1024
    }


# ============================================================
# LOGIN SCENARIOS
# ============================================================

def calculate_scenario_times(
    password_ms,
    otp_ms,
    face_ms,
    session_ms,
    sign_ms
):
    """
    Calculate server-side login scenarios.
    """

    # Traditional static authentication
    static_server = password_ms

    # Adaptive normal successful login
    adaptive_server = (
        password_ms
        + otp_ms
        + face_ms
        + session_ms
        + sign_ms
    )

    # Adaptive login with one OTP resend
    adaptive_otp_retry = (
        password_ms
        + (otp_ms * 2)
        + face_ms
        + session_ms
        + sign_ms
    )

    # Adaptive login with one face retry
    adaptive_face_retry = (
        password_ms
        + otp_ms
        + (face_ms * 2)
        + session_ms
        + sign_ms
    )

    # Three wrong password attempts
    static_three_wrong = password_ms * 3

    adaptive_three_wrong = password_ms * 3

    return {
        "Static - Normal Login": static_server,

        "Adaptive - Normal Login": adaptive_server,

        "Adaptive - 1 OTP Retry": adaptive_otp_retry,

        "Adaptive - 1 Face Retry": adaptive_face_retry,

        "Static - 3 Wrong Passwords": static_three_wrong,

        "Adaptive - 3 Wrong Passwords": adaptive_three_wrong
    }


# ============================================================
# MAIN PERFORMANCE BENCHMARK
# ============================================================

def run_performance(quick=False):

    config = eval_config.get_iterations(
        quick
    )

    n = config["n_iter"]

    print("\nBenchmarking password verification...")

    password_times = benchmark_password(
        config["n_iter_pw"]
    )

    print("Benchmarking OTP...")

    otp_times = benchmark_otp(n)

    print("Benchmarking face processing...")

    face_times = benchmark_face_server(n)

    print("Benchmarking session key generation...")

    session_times = benchmark_session_key(n)

    print("Benchmarking Dilithium signing...")

    sign_times = benchmark_signature(n)

    print("Benchmarking Dilithium verification...")

    verify_times = benchmark_signature_verification(n)

    # --------------------------------------------------------
    # Stage statistics
    # --------------------------------------------------------

    stages = {
        "Password Verification": password_times,
        "OTP Verification": otp_times,
        "Face Verification": face_times,
        "Session Key Generation": session_times,
        "PQC Signing": sign_times,
        "PQC Verification": verify_times
    }

    stage_statistics = {}

    for name, values in stages.items():

        stage_statistics[name] = {
            "mean_ms": mean(values),
            "median_ms": median(values),
            "std_ms": stdev(values),
            "p95_ms": percentile(values, 0.95),
            "min_ms": min(values),
            "max_ms": max(values)
        }

    # --------------------------------------------------------
    # Scenario calculations
    # --------------------------------------------------------

    scenario = calculate_scenario_times(
        mean(password_times),
        mean(otp_times),
        mean(face_times),
        mean(session_times),
        mean(sign_times)
    )

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    password, password_hash = password_setup()

    def cpu_test():
        check_password_hash(
            password_hash,
            password
        )

    cpu_result = measure_cpu(
        cpu_test
    )

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    memory_result = measure_memory(
        generate_session_key
    )

    # --------------------------------------------------------
    # Crypto object sizes
    # --------------------------------------------------------

    public_key, secret_key = crypto_adapter.keygen()

    message = os.urandom(32)

    signature = crypto_adapter.sign(
        secret_key,
        message
    )

    crypto_sizes = {
        "public_key_bytes": len(public_key),
        "secret_key_bytes": len(secret_key),
        "signature_bytes": len(signature),
        "session_key_bytes": 32
    }

    # --------------------------------------------------------
    # Processing cost summary
    # --------------------------------------------------------

    server_cost = {
        "cpu_elapsed_ms": cpu_result["elapsed_ms"],
        "cpu_percent": cpu_result["cpu_percent"],
        "peak_memory_kb": memory_result["peak_kb"]
    }

    # --------------------------------------------------------
    # Raw latency data
    # --------------------------------------------------------

    latency_distribution = {
        name: values
        for name, values in stages.items()
    }

    return {
        "stage_statistics": stage_statistics,
        "scenario_times": scenario,
        "server_cost": server_cost,
        "crypto_sizes": crypto_sizes,
        "latency_distribution": latency_distribution,
        "crypto_backend": crypto_adapter.backend_name()
    }


if __name__ == "__main__":

    result = run_performance(
        quick=True
    )

    print("\nPerformance benchmark completed.")

    for name, values in result["stage_statistics"].items():

        print(
            f"{name}: "
            f"{values['mean_ms']:.4f} ms"
        )