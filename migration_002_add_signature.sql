-- ============================================================
-- Objective 2 migration: adds columns to store the Dilithium
-- signature of each session key.
--
-- SAFE TO RUN on your existing database — this does NOT touch
-- the 'users' table or delete/modify any existing rows. It only
-- adds two new nullable columns to 'login_sessions'.
--
-- Run it the same way you ran schema.sql, e.g.:
--   Get-Content migration_002_add_signature.sql | & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
-- ============================================================

USE adaptive_auth;

ALTER TABLE login_sessions
    ADD COLUMN signature TEXT NULL AFTER session_key,
    ADD COLUMN signature_algo VARCHAR(30) DEFAULT 'Dilithium3' AFTER signature;
