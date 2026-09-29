# Adaptive Login Mechanism — Objective 1 (Face-Biometric Edition)

A Flask + MySQL implementation of an adaptive, 3-factor login system:

1. **Username + Password** (adapts: after 3 failed attempts, an OTP is also required for
   attempts 4 & 5; 5 total failures locks the account)
2. **Email OTP** (max 2 resends; 3rd resend locks the account)
3. **Live face match** — a personal **Google Teachable Machine** image model, trained in
   your own browser at registration time, checked against your webcam at login (max 2
   attempts, then locks)

On success, a fresh random **session key** is generated and stored, and is signed with
**CRYSTALS-Dilithium3** (Objective 2 — unchanged from before).

No real email is sent — OTPs are shown directly on the page in a "DEMO POPUP" box.

> **This replaces the earlier 3×3 dot-pattern step.** Nothing about Steps 1 (password)
> or 2 (OTP) changed. See "What changed from the pattern version" below.

---

## 1. Install MySQL Server (skip if already installed)

### Windows
1. Download the MySQL Installer from https://dev.mysql.com/downloads/installer/
2. Run it, choose **"Server only"** (or "Developer Default"), and complete setup.
3. During setup you'll set a **root password** — remember it.
4. MySQL should start automatically as a Windows service.

### macOS
```bash
brew install mysql
brew services start mysql
mysql_secure_installation   # sets a root password
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo mysql_secure_installation   # sets a root password
```

---

## 2. Create the database

**Brand-new install:**
```bash
mysql -u root -p < schema.sql
```
This creates the `adaptive_auth` database with `users` and `login_sessions` tables
(the `login_sessions` table already includes the Objective-2 signature columns).

**Upgrading an existing database from the old pattern-based version:** do NOT run
`schema.sql` (it won't touch your existing tables, but your app code no longer matches
their shape). Instead run:
```bash
mysql -u root -p < migration_003_face_biometric.sql
```
This drops `pattern_hash`, renames `failed_pattern_attempts` → `failed_face_attempts`,
and adds `face_model_path`. **Existing accounts will have no face model enrolled** —
this project doesn't include a "re-enroll" flow, so old test accounts should just be
dropped and re-registered.

---

## 3. Configure the app

Open `config.py` and set your MySQL password:
```python
DB_PASSWORD = "your_actual_mysql_password"
```
You can also tweak policy values here: password rules, the required email domain,
attempt limits, and — new — `FACE_MATCH_THRESHOLD` (how confident the model must be)
and `MAX_FACE_ATTEMPTS`.

---

## 4. Install Python dependencies

```bash
pip install -r requirements.txt
```
No new Python packages were needed for the face step — Teachable Machine training and
inference run **entirely in the browser** via TensorFlow.js, loaded from a CDN
(`@tensorflow/tfjs@1.3.1` + `@teachablemachine/image@0.8.5`, pinned versions, no build
step required). Your machine needs internet access on first page load for those two
`<script>` tags; after that the base MobileNet weights are cached by the browser.

---

## 5. Run the app

```bash
python app.py
```
Open your browser at **http://127.0.0.1:5000** — Chrome/Edge/Firefox all work; the
browser will ask for camera permission on the face pages.

---

## How the face step actually works

**Registration (`/register` → `/register/face`):**
1. You enter username/email/password as before. Nothing is written to the database yet
   — it's held in your Flask session until enrollment succeeds, so there's never a
   half-registered account sitting in the DB.
2. On the enrollment page, your browser asks for camera access and captures two short
   bursts of webcam frames:
   - **"Face"** — ~36 frames while you look at the camera and move/tilt your head.
   - **"Not Face"** — ~36 frames of *not* your face (point the camera away, hold up
     your hand, show a wall). This negative class is what lets the model tell "face
     present" from "face absent" — Teachable Machine has no built-in notion of faces,
     it just learns to tell your two example sets apart.
3. Your browser then trains a small classifier on top of a frozen MobileNet feature
   extractor (transfer learning), fully client-side, using the same open-source
   `@teachablemachine/image` library that powers teachablemachine.withgoogle.com. This
   takes roughly 15–30 seconds depending on your machine.
4. The trained model is exported to the exact same file formats the Teachable Machine
   website itself produces — `model.json`, `weights.bin`, `metadata.json` — and
   uploaded. **Only at this point** does the server create your account and save these
   three files to `face_models/<user_id>/`.

**Login (`/login/face`, Step 3):**
1. Your browser loads *your own* `model.json`/`weights.bin`/`metadata.json` (fetched
   through an access-gated route, not a public static path — see "Security notes"
   below) and runs live predictions against your webcam for ~1.2 seconds (8 frames),
   averaging the result.
2. The averaged `{"Face": p, "Not Face": 1-p}` probabilities are sent to the server,
   which independently re-checks them against `config.FACE_MATCH_THRESHOLD` (default
   0.90) before accepting — the server never just trusts a bare "pass/fail" boolean
   from the browser.
3. Two failed attempts locks the account, exactly like the old pattern step.

### Old shared `model.json` / `weights.bin` (labels: Tanya / Iphone)
These came from a single shared demo model and have been **completely removed**. Every
user now gets their own model, trained from their own captures, stored under their own
`face_models/<user_id>/` folder.

---

## Security notes / honest limitations

This is a coursework/demo project, and the face step in particular has a real trust
boundary worth understanding rather than glossing over:

- **Inference is client-side.** Teachable Machine models run in the browser by design.
  That means the "did this match?" probabilities are computed by JavaScript the user's
  own browser is running, then POSTed to the server. A technically sophisticated user
  could, in principle, open devtools and POST a forged `predictions` payload without
  ever showing their face — the same fundamental trust issue the old pattern step had
  (its value was also read out of the DOM and posted by client JS). Mitigations already
  included: the server re-applies the real threshold rather than trusting a boolean;
  each attempt requires a fresh single-use `challenge` token issued by the server (so a
  captured request can't just be replayed); probabilities are sanity-checked to sum to
  ~1. None of this makes it unspoofable — for a production system you'd add server-side
  re-inference of the raw frame (e.g. via `tfjs-node`, or converting the export to a
  format a Python ML stack can run) so the server, not the browser, makes the final call.
- **This is an image-similarity classifier, not biometric-grade face recognition.**
  Teachable Machine has no concept of facial landmarks, liveness, or anti-spoofing — it
  learned to distinguish two example sets you gave it. A photo of your face held up to
  the camera may well pass. Good enough to demonstrate an adaptive-auth pipeline; not a
  substitute for a real biometric SDK in production.
- **Model files are access-gated, not public.** They're served through
  `/face-model/<user_id>/<filename>`, which checks that the requesting session is either
  that pending login or that logged-in user — not dropped under `/static/` where any
  visitor could enumerate user ids and download every model.
- Everything else — password hashing (bcrypt), OTP flow, lockout counters, and the
  Objective-2 Dilithium3 signing — is unchanged from the earlier version.

---

## To manually unlock a locked test account (demo only)

```sql
USE adaptive_auth;
UPDATE users SET is_locked = FALSE,
                 failed_password_attempts = 0,
                 otp_resend_count = 0,
                 failed_face_attempts = 0
WHERE username = 'your_test_username';
```

To fully reset a test account including its face model:
```sql
DELETE FROM users WHERE username = 'your_test_username';
```
and delete its folder under `face_models/<old_user_id>/` (the id is reused by MySQL
auto-increment logic only if you reset the table, so this is usually safe to skip).

---

## Project structure

```
adaptive_login/
├── app.py                          # Flask routes / application logic
├── db.py                           # All MySQL queries
├── auth_utils.py                   # Password hashing, validation, OTP, challenge tokens
├── face_utils.py                   # Face-model file storage + server-side threshold checks
├── dilithium_utils.py              # Objective 2: keygen / sign / verify
├── config.py                       # DB credentials + policy constants
├── schema.sql                      # Canonical schema for a fresh install
├── migration_003_face_biometric.sql# Upgrade path from the old pattern-based DB
├── migration_002_add_signature.sql # (kept for reference — folded into schema.sql now)
├── requirements.txt
├── templates/
│   ├── welcome.html
│   ├── register.html               # Step 1: username/email/password
│   ├── register_face.html          # Step 2: webcam capture + in-browser training
│   ├── register_success.html
│   ├── login_step1.html
│   ├── login_step2_otp.html
│   ├── login_step3_face.html       # live webcam verification
│   ├── login_success.html
│   ├── locked.html
│   ├── verify_session.html
│   └── verify_session_visual.html
├── static/
│   ├── css/style.css
│   └── js/
│       ├── face_register.js        # capture, train, export, upload
│       └── face_login.js           # load model, live-predict, submit
└── face_models/                    # auto-created; per-user model.json/weights.bin/metadata.json
```

## Notes / assumptions made

- Password rule: min 8 chars, ≥1 uppercase, ≥1 digit (adjust in `auth_utils.is_valid_password`).
- Email rule: must end in `@company.com` (change `ALLOWED_EMAIL_DOMAIN` in `config.py`).
- Negative-class capture strategy: guided "point the camera away from your face" frames,
  the standard approach recommended for a Teachable Machine presence-classifier when
  a second real face isn't available to use as a negative example during solo
  registration.
- OTP delivery is still a demo popup — swapping in real email is a small, isolated
  change to two spots in `app.py`, unchanged from before.
- No "forgot my face" / re-enrollment flow was requested, so none is included; an
  account with a locked or lost face model currently needs to be deleted and
  re-registered.

---

## Objective 2 — Post-Quantum Signed Sessions (unchanged)

Every session key generated at the end of a successful login is signed with
**CRYSTALS-Dilithium3** (via the pure-Python `dilithium-py` library). On first run, the
app auto-generates a server Dilithium3 keypair into `keys/` (`dilithium_public.key`,
`dilithium_private.key`) — these persist across restarts; don't delete this folder or
previously issued signatures will stop verifying. Nothing about signing/verifying
changed when the pattern step was replaced with the face step — it still signs whatever
session key Step 3 produces, whichever Step 3 happens to be.

Once you've confirmed this works the way you want, the next phase (**Objective 3**) was
planned as comparing login time and processing cost against a traditional static
authentication system.
