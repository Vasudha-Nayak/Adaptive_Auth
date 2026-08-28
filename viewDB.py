import sqlite3
conn = sqlite3.connect("adaptive_auth.db")
cur = conn.cursor()

print("--- USERS ---")
for row in cur.execute("SELECT id, username, password_hash, failed_attempts, locked_until, otp_code, otp_expiry FROM users"):
    print(row)

print("--- SESSIONS ---")
for row in cur.execute("SELECT id, user_id, session_key, created_at FROM sessions"):
    print(row)

conn.close()