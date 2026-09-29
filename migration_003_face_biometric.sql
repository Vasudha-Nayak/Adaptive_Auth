-- ============================================================
-- Migration 003: replace the 3x3 pattern step with a face-biometric step.
--
-- Run this ONLY if you have an existing database from the earlier
-- (pattern-based) version of this project and want to keep your data.
-- Brand-new installs should just run schema.sql instead.
--
-- What this does:
--   1. Drops the pattern_hash column (no longer used).
--   2. Renames failed_pattern_attempts -> failed_face_attempts (same
--      counter, same 0..2 / lock-at-2 semantics as before).
--   3. Adds face_model_path, pointing at this user's trained Teachable
--      Machine model files on disk.
--
-- IMPORTANT: existing users have no face model yet (face_model_path will
-- be NULL). They will need to re-register, or you'll need to add a
-- "re-enroll face" flow — this project does not include one, since it
-- wasn't asked for. See README for notes.
--
-- Run it the same way you ran schema.sql / migration_002, e.g.:
--   Get-Content migration_003_face_biometric.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
-- ============================================================

USE adaptive_auth;

ALTER TABLE users
    DROP COLUMN pattern_hash,
    CHANGE COLUMN failed_pattern_attempts failed_face_attempts INT DEFAULT 0,
    ADD COLUMN face_model_path VARCHAR(255) DEFAULT NULL AFTER password_hash;
