"""
bench_security.py
-----------------
Objective 3 - Security Evaluation

Measures/tests:

    1. Password brute-force resistance (MODELED)
    2. Account takeover probability (MODELED)
    3. Signature integrity
    4. Session-key uniqueness
    5. Face FAR/FRR/EER if real face-score data is supplied

Important:
    Modeled security results are clearly separated from
    directly measured cryptographic integrity tests.
"""

import csv
import math
import os
import random
from pathlib import Path

import numpy as np

import eval_config
import crypto_adapter


# ============================================================
# SESSION KEY UNIQUENESS
# ============================================================

def session_key_uniqueness(n):

    keys = set()

    duplicates = 0

    for _ in range(n):

        key = os.urandom(32)

        key_hex = key.hex()

        if key_hex in keys:
            duplicates += 1
        else:
            keys.add(key_hex)

    unique = len(keys)

    uniqueness_percentage = (
        unique / n * 100
        if n > 0
        else 0
    )

    return {
        "total_generated": n,
        "unique_keys": unique,
        "duplicates": duplicates,
        "uniqueness_percentage": uniqueness_percentage
    }


# ============================================================
# SIGNATURE INTEGRITY
# ============================================================

def signature_integrity():

    return crypto_adapter.integrity_test()


# ============================================================
# PASSWORD BRUTE FORCE MODEL
# ============================================================

def password_success_probability(
    guesses,
    vocabulary_size
):
    """
    Simplified probability model.

    P(success) = guesses / vocabulary_size

    capped at 1.
    """

    return min(
        guesses / vocabulary_size,
        1.0
    )


def brute_force_curve():

    guesses = [
        1,
        10,
        100,
        1000,
        10000,
        100000,
        1000000
    ]

    rows = []

    for g in guesses:

        probability = password_success_probability(
            g,
            eval_config.VOCAB
        )

        rows.append({
            "guesses": g,
            "success_probability": probability
        })

    return rows


# ============================================================
# TAKEOVER PROBABILITY
# ============================================================

def takeover_probability():

    """
    Modeled attack scenarios.

    These are NOT measured attack success rates.

    The calculation assumes independent factors.
    """

    p_password = (
        eval_config.ATTEMPT_BUDGET
        / eval_config.VOCAB
    )

    p_password = min(
        p_password,
        1.0
    )

    p_otp = eval_config.P_MAILBOX

    p_face = eval_config.FAR_DEFAULT

    # Traditional system:
    # password only
    traditional = p_password

    # Adaptive system:
    # password + OTP + face
    adaptive = (
        p_password
        * p_otp
        * p_face
    )

    return [
        {
            "scenario": "Static Password Only",
            "probability": traditional
        },
        {
            "scenario": "Adaptive Password + OTP + Face",
            "probability": adaptive
        }
    ]


# ============================================================
# SECURITY FEATURES
# ============================================================

def security_features():

    return [
        {
            "feature": "Adaptive authentication",
            "static_system": "No",
            "adaptive_system": "Yes"
        },
        {
            "feature": "OTP after failed attempts",
            "static_system": "No",
            "adaptive_system": "Yes"
        },
        {
            "feature": "Face verification",
            "static_system": "No",
            "adaptive_system": "Yes"
        },
        {
            "feature": "Fresh session key",
            "static_system": "No",
            "adaptive_system": "Yes"
        },
        {
            "feature": "Post-quantum signature",
            "static_system": "No",
            "adaptive_system": "Yes"
        },
        {
            "feature": "Account lockout",
            "static_system": "Optional",
            "adaptive_system": "Yes"
        }
    ]


# ============================================================
# FACE SCORE ANALYSIS
# ============================================================

def load_face_scores(path):

    path = Path(path)

    if not path.exists():
        return None

    genuine = []
    impostor = []

    with open(
        path,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            label = row["label"].strip().lower()
            score = float(row["score"])

            if label == "genuine":
                genuine.append(score)

            elif label == "impostor":
                impostor.append(score)

    return {
        "genuine": genuine,
        "impostor": impostor
    }


def calculate_face_metrics(
    genuine,
    impostor,
    threshold
):

    genuine = np.array(genuine)
    impostor = np.array(impostor)

    if len(genuine) == 0 or len(impostor) == 0:
        return None

    # Genuine accepted above threshold
    true_accepts = np.sum(
        genuine >= threshold
    )

    # Genuine rejected
    false_rejects = np.sum(
        genuine < threshold
    )

    # Impostors incorrectly accepted
    false_accepts = np.sum(
        impostor >= threshold
    )

    true_rejects = np.sum(
        impostor < threshold
    )

    far = (
        false_accepts / len(impostor)
    )

    frr = (
        false_rejects / len(genuine)
    )

    return {
        "threshold": threshold,
        "far": float(far),
        "frr": float(frr),
        "genuine_count": len(genuine),
        "impostor_count": len(impostor),
        "true_accepts": int(true_accepts),
        "false_rejects": int(false_rejects),
        "false_accepts": int(false_accepts),
        "true_rejects": int(true_rejects)
    }


def face_roc(
    genuine,
    impostor
):

    genuine = np.array(genuine)
    impostor = np.array(impostor)

    thresholds = np.linspace(
        0,
        1,
        101
    )

    rows = []

    for threshold in thresholds:

        false_accepts = np.sum(
            impostor >= threshold
        )

        true_rejects = np.sum(
            impostor < threshold
        )

        true_accepts = np.sum(
            genuine >= threshold
        )

        false_rejects = np.sum(
            genuine < threshold
        )

        far = (
            false_accepts / len(impostor)
            if len(impostor)
            else 0
        )

        tpr = (
            true_accepts / len(genuine)
            if len(genuine)
            else 0
        )

        frr = (
            false_rejects / len(genuine)
            if len(genuine)
            else 0
        )

        rows.append({
            "threshold": threshold,
            "far": float(far),
            "frr": float(frr),
            "tpr": float(tpr)
        })

    return rows


# ============================================================
# MAIN SECURITY BENCHMARK
# ============================================================

def run_security(quick=False):

    config = eval_config.get_iterations(
        quick
    )

    print("\nTesting PQ signature integrity...")

    integrity = signature_integrity()

    print("Testing session-key uniqueness...")

    session_keys = session_key_uniqueness(
        config["n_session_keys"]
    )

    print("Generating brute-force model...")

    brute_force = brute_force_curve()

    print("Generating takeover model...")

    takeover = takeover_probability()

    features = security_features()

    # --------------------------------------------------------
    # Optional real face data
    # --------------------------------------------------------

    face_data = None
    face_metrics = None
    roc = None

    face_csv = (
        Path(__file__).resolve().parent
        / "face_scores.csv"
    )

    if face_csv.exists():

        print(
            "Real face-score dataset found."
        )

        face_data = load_face_scores(
            face_csv
        )

        face_metrics = calculate_face_metrics(
            face_data["genuine"],
            face_data["impostor"],
            eval_config.FACE_THRESHOLD
        )

        roc = face_roc(
            face_data["genuine"],
            face_data["impostor"]
        )

    else:

        print(
            "No face_scores.csv found."
        )

        print(
            "Face ROC will be skipped."
        )

    return {
        "integrity": integrity,
        "session_keys": session_keys,
        "brute_force": brute_force,
        "takeover": takeover,
        "features": features,
        "face_metrics": face_metrics,
        "face_roc": roc,
        "crypto_backend":
            crypto_adapter.backend_name()
    }


if __name__ == "__main__":

    result = run_security(
        quick=True
    )

    print("\nSecurity evaluation completed.")

    print(
        "\nSession key uniqueness:",
        result["session_keys"]
    )

    print(
        "\nSignature integrity:",
        result["integrity"]
    )