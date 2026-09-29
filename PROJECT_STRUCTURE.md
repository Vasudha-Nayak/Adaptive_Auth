# Adaptive Login with Face Biometrics: Project Structure

This document describes the folder layout of the project and what belongs where. Descriptions are based on file names and locations, so adjust any wording that doesn't match how your code actually works.

---

## 1. Directory Tree

```
adaptive_login_face_biometric/
│
├── app.py                          # Main Flask application (routes, login/registration flow)
├── auth_utils.py                   # Authentication helpers (passwords, OTP, sessions)
├── config.py                       # Configuration and settings
├── db.py                           # Database connection and queries
├── dilithium_utils.py              # Dilithium post-quantum signature helpers
├── face_utils.py                   # Face biometric helpers (embeddings, matching)
├── schema.sql                      # Base database schema
├── migration_003_face_biometric.sql# Migration adding face biometric tables/columns
├── requirements.txt                # Python dependencies
├── README.md                       # Main project README
├── .gitignore                      # Files/folders excluded from Git
│
├── __pycache__/                    # Auto-generated Python bytecode (do not edit)
│   ├── auth_utils.cpython-313.pyc
│   ├── config.cpython-313.pyc
│   ├── db.cpython-313.pyc
│   ├── dilithium_utils.cpython-313.pyc
│   └── face_utils.cpython-313.pyc
│
├── face_models/                    # Stored face models, one sub-folder per user
│   ├── 1/
│   │   ├── metadata.json           # Info about the saved model
│   │   ├── model.json              # Model architecture/definition
│   │   └── weights.bin             # Trained model weights (~5.7 MB)
│   ├── 2/                          # Same layout as folder 1
│   └── 3/                          # Same layout as folder 1
│
├── keys/                           # Cryptographic key pair
│   ├── dilithium_private.key       # PRIVATE signing key (keep secret)
│   └── dilithium_public.key        # Public verification key
│
├── static/                         # Files served directly to the browser
│   ├── css/
│   │   └── style.css               # Global stylesheet
│   └── js/
│       ├── face_login.js           # Webcam capture + face verification at login
│       └── face_register.js        # Webcam capture + face enrollment at registration
│
└── templates/                      # HTML pages (Jinja2 templates rendered by Flask)
    ├── register.html               # Registration form
    ├── register_face.html          # Face enrollment step
    ├── register_success.html       # Registration complete
    ├── login_step1.html            # Login step 1 (credentials)
    ├── login_step2_otp.html        # Login step 2 (OTP verification)
    ├── login_step3_face.html       # Login step 3 (face verification)
    ├── login_success.html          # Login complete
    ├── verify_session.html         # Session verification page
    ├── verify_session_visual.html  # Visual/face-based session re-verification
    ├── locked.html                 # Account locked page
    └── welcome.html                # Landing/welcome page
```

---

## 2. Root-Level Files

| File | Purpose |
|------|---------|
| `app.py` | The main application entry point (~22 KB). Defines the routes and ties together the registration, multi-step login, and session verification flows. Run this to start the server. |
| `auth_utils.py` | Authentication helper functions used by `app.py`. |
| `config.py` | Central settings (secret keys, thresholds, paths, database settings). |
| `db.py` | Database connection and query functions. |
| `dilithium_utils.py` | Functions for generating, loading, signing with, and verifying using the Dilithium keys in `keys/`. |
| `face_utils.py` | Face-related logic: loading models from `face_models/`, processing images, comparing faces. |
| `schema.sql` | Initial database schema. Run this first when setting up. |
| `migration_003_face_biometric.sql` | Migration that adds face biometric support to the schema. Run after `schema.sql`. |
| `requirements.txt` | Python packages to install with `pip install -r requirements.txt`. |
| `README.md` | Main project documentation. |
| `.gitignore` | Lists files Git should not track. |

---

## 3. Folders in Detail

### `face_models/`
Holds one sub-folder per user, named by numeric ID (`1`, `2`, `3`). Each contains three files, which together look like a TensorFlow.js-style saved model:

- `model.json`: model architecture
- `weights.bin`: weights
- `metadata.json`: extra info about the model

Only folder `1` is visible in your screenshots; `2` and `3` are assumed to match.

### `keys/`
Holds the Dilithium key pair. The private key must stay secret, and the public key can be shared.

### `static/`
Browser-facing assets. Flask serves these from `/static/...`.
- `css/style.css` holds the styling for all pages.
- `js/face_register.js` runs on the face enrollment page.
- `js/face_login.js` runs on the face verification page during login.

### `templates/`
HTML pages that Flask renders. They map to the two main flows:

**Registration flow**
`register.html` → `register_face.html` → `register_success.html`

**Login flow (adaptive, multi-step)**
`login_step1.html` → `login_step2_otp.html` → `login_step3_face.html` → `login_success.html`

**Other pages**
- `verify_session.html` / `verify_session_visual.html`: session re-verification
- `locked.html`: shown when an account is locked
- `welcome.html`: landing page

### `__pycache__/`
Created automatically by Python (version 3.13 here). Safe to delete; it regenerates on the next run. It should be listed in `.gitignore`.

---

## 4. Where New Files Should Go

| If you're adding... | Put it in... |
|---------------------|--------------|
| A new page | `templates/` |
| Browser JavaScript | `static/js/` |
| Styles | `static/css/` |
| Backend logic helpers | Project root, alongside `auth_utils.py` etc. |
| A new database change | A new numbered migration in the root, e.g. `migration_004_...sql` |
| A user's face model | `face_models/<user_id>/` |
| Signing keys | `keys/` |

---

## 5. Security Notes

- **Do not commit `keys/dilithium_private.key`.** Confirm that `keys/` (or at least the private key) is listed in `.gitignore`.
- **`face_models/` contains biometric data.** Treat it as sensitive: exclude it from Git and restrict access on any server.
- Delete `__pycache__/` before sharing or zipping the project.

---

## 6. Quick Start

```bash
pip install -r requirements.txt
# Set up the database: run schema.sql, then migration_003_face_biometric.sql
python app.py
```
