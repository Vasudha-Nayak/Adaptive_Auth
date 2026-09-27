# Adaptive Login Mechanism — Objective 1

A Flask + MySQL implementation of an adaptive, 3-factor login system:

1. **Username + Password** (adapts: after 3 failed attempts, an OTP is also required for
   attempts 4 & 5; 5 total failures locks the account)
2. **Email OTP** (max 2 resends; 3rd resend locks the account)
3. **Pattern match** (3x3 dot grid, assigned at registration; max 2 attempts, then locks)

On success, a fresh random **session key** is generated and stored — this is the value that
will be secured with **CRYSTALS-Dilithium** in the next project phase (Objective 2).

No real email is sent yet — OTPs are shown directly on the page in a "DEMO POPUP" box, as
you requested.

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

Open a terminal and log into MySQL:

```bash
mysql -u root -p
```

Then run the schema file (either paste its contents, or from your OS shell run):

```bash
mysql -u root -p < schema.sql
```

This creates the `adaptive_auth` database with `users` and `login_sessions` tables.

---

## 3. Configure the app

Open `config.py` and set your MySQL password:

```python
DB_PASSWORD = "your_actual_mysql_password"
```

(Also adjust `DB_USER` / `DB_HOST` if your setup differs from the default `root` @ `localhost`.)

You can also tweak policy values here: password complexity rules, the required email domain
(`company.com` by default), attempt limits, and pattern length.

---

## 4. Install Python dependencies

From the project folder:

```bash
pip install -r requirements.txt
```

---

## 5. Run the app

```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## How to test the flows

- **Register** with an email like `test@company.com` and a password like `Passw0rd1`.
  You'll be shown a pattern (e.g. `2 → 5 → 8 → 9`) — **write it down**, it's only shown once.
- **Login**:
  - Step 1: enter your username/password. Enter it wrong 3 times in a row and you'll see the
    adaptive OTP field appear — enter the demo OTP shown, plus your correct password.
  - Step 2: enter the OTP shown in the demo popup (or click Resend to test the resend-limit lockout).
  - Step 3: click the dots in your pattern's exact order, then Submit.
- On success you'll see your freshly generated session key.

## To manually unlock a locked test account (demo only)

```sql
USE adaptive_auth;
UPDATE users SET is_locked = FALSE,
                 failed_password_attempts = 0,
                 otp_resend_count = 0,
                 failed_pattern_attempts = 0
WHERE username = 'your_test_username';
```

---

## Project structure

```
adaptive_login/
├── app.py                 # Flask routes / application logic
├── db.py                  # All MySQL queries
├── auth_utils.py          # Hashing, validation, OTP & pattern generation
├── config.py               # DB credentials + policy constants
├── schema.sql              # MySQL table definitions
├── requirements.txt
├── templates/               # Jinja2 HTML pages
└── static/
    ├── css/style.css
    └── js/pattern.js        # Interactive pattern grid
```

## Notes / assumptions made

- Password rule: min 8 chars, ≥1 uppercase, ≥1 digit (adjust in `auth_utils.is_valid_password`).
- Email rule: must end in `@company.com` (change `ALLOWED_EMAIL_DOMAIN` in `config.py`).
- The pattern is **system-generated and shown to the user** at registration (not user-drawn),
  matching "a pattern to be prompted at random to the user."
- OTP delivery is a demo popup for now — swapping in real email (e.g. via `smtplib` / SendGrid)
  is a small, isolated change to two spots in `app.py` once you're ready.

---

## Objective 2 — Post-Quantum Signed Sessions (NEW)

Every session key generated at the end of a successful login is now signed with
**CRYSTALS-Dilithium3** (via the pure-Python `dilithium-py` library — no C
compiler needed). This proves the session was genuinely issued by the server and
lets it be verified against tampering, even by a future quantum-capable attacker.

**This was added without changing any Objective 1 behavior** — registration, the
3-step login, and all lockout rules work exactly as before. Only one line was
added at the point the session key was already being created.

### Setup (one extra step)

1. Install the new dependency:
   ```
   pip install -r requirements.txt
   ```
   (this now also installs `dilithium-py`)

2. Run the migration to add the signature column (safe — does not touch existing data):
   ```
   Get-Content migration_002_add_signature.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
   ```

3. Run the app as usual: `python app.py`

On first run, the app auto-generates a server Dilithium3 keypair into a new
`keys/` folder (`dilithium_public.key`, `dilithium_private.key`). These persist
across restarts — **do not delete this folder**, or previously issued
signatures will no longer verify.

### How to see it in action

After completing all 3 login steps, the success page shows a "Session Signed —
Quantum-Resistant" badge. Click **Verify Signature** to:
- Re-verify the real signature live (should show ✅ VALID)
- Click **Simulate Tampering & Verify** to alter the session key by one
  character and watch it correctly show ❌ INVALID — demonstrating that
  Dilithium detects any tampering.

### New files
```
dilithium_utils.py               # keygen / sign / verify (server-wide keypair)
migration_002_add_signature.sql  # adds signature + signature_algo columns
keys/                            # auto-created, holds the server keypair
templates/verify_session.html    # live verification demo page
```

Once you've confirmed this works the way you want, we'll move on to
**Objective 3**: comparing login time and processing cost against a traditional
static authentication system.
