"""
Server-side helpers for the face-biometric step (Objective 1, Step 3).

IMPORTANT — what this module does and doesn't do:
  - It never processes an actual photo/frame on the server. The Teachable
    Machine model is trained AND run entirely in the browser (that's the
    whole point of Teachable Machine). This module only stores each user's
    exported model files, and sanity-checks + threshold-checks the
    prediction result the browser reports back.
  - Because inference happens client-side, a technically sophisticated user
    could in theory forge the POST body without ever showing their face to
    the camera (same trust boundary the old pattern step had, since that
    too was a value read out of the DOM by JS and posted to the server).
    This is a known limitation of pure client-side biometrics — see the
    README for mitigations already in place and what you'd add for a
    production system (server-side re-inference of the raw frame).
"""
import os
import re
import shutil

import config

_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def user_model_dir(user_id: int) -> str:
    return os.path.join(config.FACE_MODEL_DIR, str(int(user_id)))


def model_exists(user_id: int) -> bool:
    d = user_model_dir(user_id)
    return all(os.path.isfile(os.path.join(d, fname)) for fname in config.FACE_MODEL_FILENAMES)


def save_model_files(user_id: int, model_json_bytes: bytes, weights_bin_bytes: bytes, metadata_json_bytes: bytes) -> str:
    """Writes the three exported Teachable Machine files for this user.
    Returns the relative path stored in users.face_model_path."""
    d = user_model_dir(user_id)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "model.json"), "wb") as f:
        f.write(model_json_bytes)
    with open(os.path.join(d, "weights.bin"), "wb") as f:
        f.write(weights_bin_bytes)
    with open(os.path.join(d, "metadata.json"), "wb") as f:
        f.write(metadata_json_bytes)
    return os.path.join("face_models", str(int(user_id)))


def delete_model_files(user_id: int) -> None:
    d = user_model_dir(user_id)
    if os.path.isdir(d):
        shutil.rmtree(d, ignore_errors=True)


def safe_model_filename(filename: str) -> bool:
    """Whitelist check before send_from_directory — only allow the three
    exact known filenames, no path traversal."""
    return filename in config.FACE_MODEL_FILENAMES and bool(_SAFE_FILENAME.match(filename))


def validate_metadata(metadata: dict) -> bool:
    """Sanity-check the metadata.json the browser generated after training:
    exactly 2 labels, containing our two expected class names."""
    if not isinstance(metadata, dict):
        return False
    labels = metadata.get("labels")
    if not isinstance(labels, list) or len(labels) != 2:
        return False
    normalized = {str(l).strip().lower() for l in labels}
    expected = {config.FACE_CLASS_LABEL.lower(), config.NOT_FACE_CLASS_LABEL.lower()}
    return normalized == expected


def evaluate_prediction(predictions) -> tuple:
    """
    predictions: list of {"className": str, "probability": float} as reported
    by tmImage's CustomMobileNet.predict() in the browser (one entry per class).

    Returns (passed: bool, face_probability: float, reason: str)
    """
    if not isinstance(predictions, list) or len(predictions) != 2:
        return False, 0.0, "malformed prediction payload"

    by_label = {}
    total = 0.0
    for p in predictions:
        try:
            label = str(p.get("className", "")).strip()
            prob = float(p.get("probability", 0))
        except (AttributeError, TypeError, ValueError):
            return False, 0.0, "malformed prediction entry"
        if not (0.0 <= prob <= 1.0):
            return False, 0.0, "probability out of range"
        by_label[label] = prob
        total += prob

    # probabilities from a softmax layer should sum to ~1
    if not (0.9 <= total <= 1.1):
        return False, 0.0, "probabilities do not sum to ~1 (forged payload?)"

    if config.FACE_CLASS_LABEL not in by_label or config.NOT_FACE_CLASS_LABEL not in by_label:
        return False, 0.0, "expected class labels not present"

    face_prob = by_label[config.FACE_CLASS_LABEL]
    not_face_prob = by_label[config.NOT_FACE_CLASS_LABEL]

    passed = face_prob >= config.FACE_MATCH_THRESHOLD and face_prob > not_face_prob
    return passed, face_prob, ("ok" if passed else "confidence below threshold")
