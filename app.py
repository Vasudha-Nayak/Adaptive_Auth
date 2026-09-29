"""
Adaptive Login Mechanism - Objective 1 (+ Objective 2 signed sessions)
Step 3 is now a face-biometric check (Google Teachable Machine) instead of
a 3x3 dot pattern.

Run with: python app.py
Then open http://127.0.0.1:5000
"""
import hashlib
import json
import os

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    jsonify, send_from_directory, abort,
)

import config
import db
import auth_utils
import face_utils
import dilithium_utils

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Hard cap on the multipart upload of a trained model (weights.bin is the
# biggest piece; MobileNet-based TM models are typically a few MB).
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB


@app.context_processor
def inject_config():
    """Lets templates read policy constants directly, e.g. {{ config.ALLOWED_EMAIL_DOMAIN }}."""
    return {"config": config}


# ============================================================
# WELCOME
# ============================================================

@app.route("/")
def welcome():
    return render_template("welcome.html")


# ============================================================
# REGISTRATION - STEP 1: username / email / password
# (No DB row is created yet — held in session until the face model
#  in Step 2 is successfully trained and uploaded.)
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # --- validation ---
        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if not auth_utils.is_valid_email(email):
            flash(f"Email must be a valid @{config.ALLOWED_EMAIL_DOMAIN} address (e.g. xyz@{config.ALLOWED_EMAIL_DOMAIN}).", "error")
            return render_template("register.html")

        if not auth_utils.is_valid_password(password):
            flash("Password must be at least 8 characters and include an uppercase letter and a number.", "error")
            return render_template("register.html")

        if db.get_user_by_username(username):
            flash("That username is already taken.", "error")
            return render_template("register.html")

        if db.get_user_by_email(email):
            flash("This email is already registered. You cannot register the same email twice.", "error")
            return render_template("register.html")

        # Stash the pending registration (never the raw password) — the
        # account itself isn't created until face enrollment succeeds.
        session["pending_reg"] = {
            "username": username,
            "email": email,
            "password_hash": auth_utils.hash_value(password),
        }
        return redirect(url_for("register_face"))

    return render_template("register.html")


# ============================================================
# REGISTRATION - STEP 2: face biometric enrollment (Teachable Machine)
# ============================================================

@app.route("/register/face", methods=["GET", "POST"])
def register_face():
    pending = session.get("pending_reg")
    if not pending:
        flash("Please start registration from the beginning.", "error")
        return redirect(url_for("register"))

    if request.method == "GET":
        return render_template(
            "register_face.html",
            username=pending["username"],
            face_label=config.FACE_CLASS_LABEL,
            not_face_label=config.NOT_FACE_CLASS_LABEL,
        )

    # --- POST: browser has trained the model and is uploading the export ---
    model_file = request.files.get("model_json")
    weights_file = request.files.get("weights_bin")
    metadata_raw = request.form.get("metadata_json", "")

    if not model_file or not weights_file or not metadata_raw:
        flash("Face model upload was incomplete. Please retrain and try again.", "error")
        return render_template(
            "register_face.html",
            username=pending["username"],
            face_label=config.FACE_CLASS_LABEL,
            not_face_label=config.NOT_FACE_CLASS_LABEL,
        )

    try:
        metadata = json.loads(metadata_raw)
    except (ValueError, TypeError):
        flash("Face model metadata was invalid. Please retrain and try again.", "error")
        return render_template(
            "register_face.html",
            username=pending["username"],
            face_label=config.FACE_CLASS_LABEL,
            not_face_label=config.NOT_FACE_CLASS_LABEL,
        )

    if not face_utils.validate_metadata(metadata):
        flash("Trained model did not have the expected classes. Please retrain and try again.", "error")
        return render_template(
            "register_face.html",
            username=pending["username"],
            face_label=config.FACE_CLASS_LABEL,
            not_face_label=config.NOT_FACE_CLASS_LABEL,
        )

    model_json_bytes = model_file.read()
    weights_bytes = weights_file.read()

    if not model_json_bytes or not weights_bytes:
        flash("Face model upload was empty. Please retrain and try again.", "error")
        return render_template(
            "register_face.html",
            username=pending["username"],
            face_label=config.FACE_CLASS_LABEL,
            not_face_label=config.NOT_FACE_CLASS_LABEL,
        )

    # Only now, with a real trained model in hand, do we create the account.
    new_id = db.create_user(
        pending["username"],
        pending["email"],
        pending["password_hash"],
        face_model_path=None,  # filled in right after, once we know new_id
    )

    face_model_path = face_utils.save_model_files(
        new_id, model_json_bytes, weights_bytes, metadata_raw.encode("utf-8")
    )

    # store the path now that the user id (and therefore the folder) exists
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET face_model_path = %s WHERE id = %s", (face_model_path, new_id))
    conn.commit()
    cur.close()
    conn.close()

    session.pop("pending_reg", None)
    session["reveal_username"] = pending["username"]
    return redirect(url_for("register_success"))


@app.route("/register/success")
def register_success():
    username = session.pop("reveal_username", None)
    if not username:
        return redirect(url_for("welcome"))
    return render_template("register_success.html", username=username)


# ============================================================
# LOGIN - STEP 1: username + password (adaptive OTP kicks in after 3 fails)
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        session.pop("adaptive_stage", None)
        session.pop("adaptive_otp", None)
        session.pop("adaptive_username", None)
        return render_template("login_step1.html", require_otp=False)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    submitted_otp = request.form.get("otp")  # only present once adaptive stage is shown

    user = db.get_user_by_username(username)
    if not user:
        flash("Invalid username or password.", "error")
        return render_template("login_step1.html", require_otp=False)

    if user["is_locked"]:
        return redirect(url_for("locked"))

    adaptive_needed = user["failed_password_attempts"] >= config.ADAPTIVE_TRIGGER_AFTER

    # --- Case A: adaptive mode needed, but this submission doesn't have the OTP yet ---
    if adaptive_needed and submitted_otp is None:
        otp = auth_utils.generate_otp()
        session["adaptive_otp"] = otp
        session["adaptive_username"] = username
        flash(
            "Multiple failed attempts detected. For your security, an OTP has also been "
            "sent to your registered email. Enter your password AND the OTP below.",
            "warning",
        )
        return render_template(
            "login_step1.html",
            require_otp=True,
            username=username,
            demo_otp=otp,  # shown as a "popup" for demo purposes (no real email sending yet)
        )

    # --- Case B: adaptive mode, OTP submitted along with password ---
    if adaptive_needed and submitted_otp is not None:
        password_ok = auth_utils.check_value(password, user["password_hash"])
        otp_ok = (
            session.get("adaptive_username") == username
            and session.get("adaptive_otp") == submitted_otp
        )

        if password_ok and otp_ok:
            db.reset_failed_password(user["id"])
            session.pop("adaptive_otp", None)
            session.pop("adaptive_username", None)
            return _advance_to_step2(user)

        db.increment_failed_password(user["id"])
        user = db.get_user_by_id(user["id"])  # refresh count

        if user["failed_password_attempts"] >= config.MAX_PASSWORD_ATTEMPTS:
            db.set_locked(user["id"], True)
            return redirect(url_for("locked"))

        # regenerate a fresh OTP for the next attempt
        otp = auth_utils.generate_otp()
        session["adaptive_otp"] = otp
        session["adaptive_username"] = username
        remaining = config.MAX_PASSWORD_ATTEMPTS - user["failed_password_attempts"]
        flash(f"Incorrect password or OTP. {remaining} attempt(s) remaining before lockout.", "error")
        return render_template(
            "login_step1.html",
            require_otp=True,
            username=username,
            demo_otp=otp,
        )

    # --- Case C: normal (non-adaptive) password check ---
    password_ok = auth_utils.check_value(password, user["password_hash"])
    if password_ok:
        db.reset_failed_password(user["id"])
        return _advance_to_step2(user)

    db.increment_failed_password(user["id"])
    user = db.get_user_by_id(user["id"])

    if user["failed_password_attempts"] >= config.MAX_PASSWORD_ATTEMPTS:
        db.set_locked(user["id"], True)
        return redirect(url_for("locked"))

    remaining = config.MAX_PASSWORD_ATTEMPTS - user["failed_password_attempts"]
    flash(f"Invalid username or password. {remaining} attempt(s) remaining before lockout.", "error")
    now_adaptive = user["failed_password_attempts"] >= config.ADAPTIVE_TRIGGER_AFTER
    if now_adaptive:
        otp = auth_utils.generate_otp()
        session["adaptive_otp"] = otp
        session["adaptive_username"] = username
        flash("An OTP has also been sent to your registered email. Enter it below along with your password.", "warning")
        return render_template("login_step1.html", require_otp=True, username=username, demo_otp=otp)

    return render_template("login_step1.html", require_otp=False)


def _advance_to_step2(user):
    """Called after step 1 succeeds. Sets up the email-OTP step."""
    session["pending_user_id"] = user["id"]
    otp = auth_utils.generate_otp()
    session["step2_otp"] = otp
    return redirect(url_for("login_otp"))


# ============================================================
# LOGIN - STEP 2: email OTP (max 2 resends)
# ============================================================

@app.route("/login/otp", methods=["GET", "POST"])
def login_otp():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = db.get_user_by_id(user_id)
    if not user or user["is_locked"]:
        return redirect(url_for("locked"))

    if request.method == "GET":
        return render_template("login_step2_otp.html", email=user["email"], demo_otp=session.get("step2_otp"))

    action = request.form.get("action")

    if action == "resend":
        if user["otp_resend_count"] >= config.MAX_OTP_RESENDS:
            db.set_locked(user["id"], True)
            return redirect(url_for("locked"))
        db.increment_otp_resend(user["id"])
        user = db.get_user_by_id(user["id"])
        new_otp = auth_utils.generate_otp()
        session["step2_otp"] = new_otp
        resends_left = config.MAX_OTP_RESENDS - user["otp_resend_count"]
        flash(f"A new OTP has been sent. {resends_left} resend(s) left before lockout.", "warning")
        return render_template("login_step2_otp.html", email=user["email"], demo_otp=new_otp)

    # action == 'verify'
    submitted_otp = request.form.get("otp", "")
    if submitted_otp == session.get("step2_otp"):
        session.pop("step2_otp", None)
        return redirect(url_for("login_face"))

    flash("Incorrect OTP. Please try again or resend.", "error")
    return render_template("login_step2_otp.html", email=user["email"], demo_otp=session.get("step2_otp"))


# ============================================================
# LOGIN - STEP 3: face biometric match (max 2 attempts)
# Replaces the old 3x3 pattern step. Inference runs client-side in the
# browser (Teachable Machine); the server re-checks the reported
# probabilities against config.FACE_MATCH_THRESHOLD before accepting.
# ============================================================

@app.route("/login/face", methods=["GET", "POST"])
def login_face():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = db.get_user_by_id(user_id)
    if not user or user["is_locked"]:
        return redirect(url_for("locked"))

    if not user["face_model_path"]:
        # Shouldn't happen (accounts are only created with a model already
        # attached) but fail safe rather than 500.
        flash("No face model is enrolled for this account.", "error")
        return redirect(url_for("locked"))

    if request.method == "GET":
        challenge = auth_utils.generate_challenge_token()
        session["face_challenge"] = challenge
        return render_template(
            "login_step3_face.html",
            user_id=user["id"],
            challenge=challenge,
            face_label=config.FACE_CLASS_LABEL,
            threshold=config.FACE_MATCH_THRESHOLD,
            remaining=request.args.get("remaining", type=int),
            reason=request.args.get("reason"),
        )

    payload = request.get_json(silent=True) or {}
    submitted_challenge = payload.get("challenge")
    predictions = payload.get("predictions")

    # single-use challenge token: must match, and is consumed immediately
    expected_challenge = session.pop("face_challenge", None)
    if not expected_challenge or submitted_challenge != expected_challenge:
        return jsonify({"ok": False, "reason": "expired_challenge", "redirect": url_for("login_face")}), 400

    passed, face_prob, reason = face_utils.evaluate_prediction(predictions)

    if passed:
        session_key = auth_utils.generate_session_key()

        # Objective 2: sign the session key with the server's Dilithium3 key
        # so its authenticity can be verified against future quantum threats.
        signature = dilithium_utils.sign_session_key(session_key)

        db.store_session_key(user["id"], session_key, signature, dilithium_utils.ALGO_NAME)
        db.reset_all_counters(user["id"])

        session.pop("pending_user_id", None)
        session["logged_in_user"] = user["username"]
        session["logged_in_user_id"] = user["id"]
        session["last_session_key"] = session_key
        return jsonify({"ok": True, "redirect": url_for("login_success")})

    db.increment_failed_face(user["id"])
    user = db.get_user_by_id(user["id"])

    if user["failed_face_attempts"] >= config.MAX_FACE_ATTEMPTS:
        db.set_locked(user["id"], True)
        return jsonify({"ok": False, "locked": True, "redirect": url_for("locked")})

    remaining = config.MAX_FACE_ATTEMPTS - user["failed_face_attempts"]
    return jsonify({
        "ok": False,
        "locked": False,
        "reason": reason,
        "confidence": round(face_prob, 3),
        "remaining": remaining,
        # reload to get a fresh single-use challenge; carry the reason/remaining
        # through as query params so the reloaded page can show them
        "redirect": url_for("login_face", remaining=remaining, reason=reason),
    })


# ============================================================
# Face model file serving (access-gated — NOT under /static, so a random
# visitor can't just enumerate /static/face_models/<id>/model.json for
# every user id).
# ============================================================

@app.route("/face-model/<int:owner_id>/<path:filename>")
def face_model_file(owner_id, filename):
    allowed_ids = set()
    if session.get("pending_user_id"):
        allowed_ids.add(int(session["pending_user_id"]))
    if session.get("logged_in_user_id"):
        allowed_ids.add(int(session["logged_in_user_id"]))
    pending = session.get("pending_reg")

    # During registration the account doesn't exist yet, so the model files
    # briefly live only in the browser — this route is for LOGIN verification
    # and (harmlessly) for a user re-viewing their own successful login.
    if owner_id not in allowed_ids:
        abort(403)

    if not face_utils.safe_model_filename(filename):
        abort(404)

    directory = face_utils.user_model_dir(owner_id)
    if not os.path.isdir(directory):
        abort(404)

    return send_from_directory(directory, filename)


# ============================================================
# SUCCESS / LOCKED / LOGOUT
# ============================================================

@app.route("/login/success")
def login_success():
    username = session.get("logged_in_user")
    session_key = session.get("last_session_key")
    if not username:
        return redirect(url_for("welcome"))
    return render_template("login_success.html", username=username, session_key=session_key)


@app.route("/verify-session", methods=["GET", "POST"])
def verify_session():
    """Objective 2 demo: re-verify the Dilithium signature on the current
    session key live, and optionally simulate tampering to show detection.
    The signature is fetched fresh from the DB (not the cookie) since it's
    too large to store client-side."""
    user_id = session.get("logged_in_user_id")
    if not user_id:
        return redirect(url_for("welcome"))

    row = db.get_latest_session_for_user(user_id)
    if not row or not row.get("signature"):
        return redirect(url_for("welcome"))

    session_key = row["session_key"]
    signature = row["signature"]

    result = None
    tampered = False

    if request.method == "POST":
        tampered = request.form.get("tamper") == "1"
        check_key = session_key
        if tampered:
            # flip the last character to prove a modified key fails verification
            last = session_key[-1]
            check_key = session_key[:-1] + ("0" if last != "0" else "1")
        result = dilithium_utils.verify_session_key(check_key, signature)

    return render_template(
        "verify_session.html",
        session_key=session_key,
        signature=signature,
        result=result,
        tampered=tampered,
    )


@app.route("/verify-session/visual")
def verify_session_visual():
    """A richer, presentation-friendly version of the verification page:
    an animated flow diagram (Session Key -> Sign -> Signature -> Verify ->
    Result) plus a byte-level view demonstrating the avalanche effect when
    the session key is tampered with. Purely additive - reads the same data
    as /verify-session, changes nothing about how signing/verifying works."""
    user_id = session.get("logged_in_user_id")
    if not user_id:
        return redirect(url_for("welcome"))

    row = db.get_latest_session_for_user(user_id)
    if not row or not row.get("signature"):
        return redirect(url_for("welcome"))

    session_key = row["session_key"]
    signature = row["signature"]
    digest = hashlib.sha256(session_key.encode("utf-8")).hexdigest()

    return render_template(
        "verify_session_visual.html",
        session_key=session_key,
        signature_preview=signature[:64],
        signature_len=len(signature),
        digest=digest,
        public_key_preview=dilithium_utils.PUBLIC_KEY.hex()[:64],
        algo=dilithium_utils.ALGO_NAME,
    )


@app.route("/api/verify-session", methods=["POST"])
def api_verify_session():
    """JSON endpoint used by the visualization page's JS to animate the
    verify (and tamper) flow without a full page reload."""
    user_id = session.get("logged_in_user_id")
    if not user_id:
        return jsonify({"error": "not authenticated"}), 401

    row = db.get_latest_session_for_user(user_id)
    if not row or not row.get("signature"):
        return jsonify({"error": "no active session"}), 404

    session_key = row["session_key"]
    signature = row["signature"]

    payload = request.get_json(silent=True) or {}
    tamper = bool(payload.get("tamper"))

    check_key = session_key
    if tamper:
        last = session_key[-1]
        check_key = session_key[:-1] + ("0" if last != "0" else "1")

    valid = dilithium_utils.verify_session_key(check_key, signature)
    digest = hashlib.sha256(check_key.encode("utf-8")).hexdigest()

    return jsonify(
        {
            "session_key": check_key,
            "digest": digest,
            "signature_preview": signature[:64],
            "valid": valid,
            "tampered": tamper,
        }
    )


@app.route("/locked")
def locked():
    session.clear()
    return render_template("locked.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False, threaded=True)
