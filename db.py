"""
Database access layer. All raw SQL lives here so app.py stays clean.
"""
import mysql.connector
from mysql.connector import Error
import config


def get_connection():
    return mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )


def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


def create_user(username, email, password_hash, pattern_hash):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users (username, email, password_hash, pattern_hash)
           VALUES (%s, %s, %s, %s)""",
        (username, email, password_hash, pattern_hash),
    )
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    conn.close()
    return new_id


def set_locked(user_id, locked=True):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_locked = %s WHERE id = %s", (locked, user_id))
    conn.commit()
    cur.close()
    conn.close()


def increment_failed_password(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET failed_password_attempts = failed_password_attempts + 1 WHERE id = %s",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def reset_failed_password(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET failed_password_attempts = 0 WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def increment_otp_resend(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET otp_resend_count = otp_resend_count + 1 WHERE id = %s",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def reset_otp_resend(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET otp_resend_count = 0 WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def increment_failed_pattern(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET failed_pattern_attempts = failed_pattern_attempts + 1 WHERE id = %s",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def reset_failed_pattern(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET failed_pattern_attempts = 0 WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def reset_all_counters(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """UPDATE users SET failed_password_attempts = 0,
                             otp_resend_count = 0,
                             failed_pattern_attempts = 0
           WHERE id = %s""",
        (user_id,),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_latest_session_for_user(user_id):
    """Fetch the most recent login_sessions row for a user (used by the
    Objective 2 verify-signature page instead of storing the large signature
    in the browser cookie)."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT * FROM login_sessions WHERE user_id = %s
           ORDER BY created_at DESC, id DESC LIMIT 1""",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def store_session_key(user_id, session_key, signature=None, signature_algo=None):
    """
    Unchanged behavior when called with just (user_id, session_key) — signature
    columns stay NULL. Objective 2 passes the extra Dilithium signature too.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO login_sessions (user_id, session_key, signature, signature_algo)
           VALUES (%s, %s, %s, %s)""",
        (user_id, session_key, signature, signature_algo),
    )
    conn.commit()
    cur.close()
    conn.close()
