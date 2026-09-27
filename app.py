"""
Adaptive Login Mechanism - Objective 1
Run with: python app.py
Then open http://127.0.0.1:5000
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import hashlib

import config
import db
import auth_utils
import dilithium_utils

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ============================================================
# WELCOME
# ============================================================

@app.route("/")
def welcome():
    return render_template("welcome.html")


# ============================================================
# REGISTRATION
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
            # "if a certain mail is registering for the second time then we don't let it register"
            flash("This email is already registered. You cannot register the same email twice.", "error")
            return render_template("register.html")

        # --- create account ---
        password_hash = auth_utils.hash_value(password)
        pattern_plain = auth_utils.generate_pattern()
        pattern_hash = auth_utils.hash_value(pattern_plain)

        db.create_user(username, email, password_hash, pattern_hash)

        # stash the plaintext pattern in session ONLY to show it once on the success page
        session["reveal_pattern"] = pattern_plain
        session["reveal_username"] = username

        return redirect(url_for("register_success"))

    return render_template("register.html")


@app.route("/register/success")
def register_success():
    pattern = session.pop("reveal_pattern", None)
    username = session.pop("reveal_username", None)
    if not pattern:
        return redirect(url_for("welcome"))
    pattern_sequence = pattern.split(",")
    return render_template(
        "register_success.html",
        username=username,
        pattern_sequence=pattern_sequence,
    )


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
        return redirect(url_for("login_pattern"))

    flash("Incorrect OTP. Please try again or resend.", "error")
    return render_template("login_step2_otp.html", email=user["email"], demo_otp=session.get("step2_otp"))


# ============================================================
# LOGIN - STEP 3: pattern match (max 2 attempts)
# ============================================================

@app.route("/login/pattern", methods=["GET", "POST"])
def login_pattern():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = db.get_user_by_id(user_id)
    if not user or user["is_locked"]:
        return redirect(url_for("locked"))

    if request.method == "GET":
        return render_template("login_step3_pattern.html")

    submitted_pattern = request.form.get("pattern", "")

    if submitted_pattern and auth_utils.check_value(submitted_pattern, user["pattern_hash"]):
        # SUCCESS - full login complete
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
        # NOTE: the full signature is NOT stored in the cookie (it's several KB,
        # over the ~4KB browser cookie limit) — it's re-fetched from the DB
        # by user id whenever it's needed (see /verify-session below).
        return redirect(url_for("login_success"))

    db.increment_failed_pattern(user["id"])
    user = db.get_user_by_id(user["id"])

    if user["failed_pattern_attempts"] >= config.MAX_PATTERN_ATTEMPTS:
        db.set_locked(user["id"], True)
        return redirect(url_for("locked"))

    remaining = config.MAX_PATTERN_ATTEMPTS - user["failed_pattern_attempts"]
    flash(f"Pattern did not match. {remaining} attempt(s) remaining before lockout.", "error")
    return render_template("login_step3_pattern.html")


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
    app.run(debug=True, port=5000)
