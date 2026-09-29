-- Adaptive Login Mechanism - Database Schema
-- Run this once in MySQL to create the database and tables.
--
-- If you already have a database from the OLD (3x3 pattern) version of this
-- project, do NOT run this file against it — run migration_003_face_biometric.sql
-- instead, which alters your existing tables in place without losing data.

CREATE DATABASE IF NOT EXISTS adaptive_auth;
USE adaptive_auth;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Objective 1, Step 3: face biometric (replaces the old 3x3 pattern).
    -- Relative path to this user's trained Teachable Machine model files,
    -- e.g. 'face_models/7'. NULL only ever transiently — a user row is not
    -- created until the model has already been trained and uploaded.
    face_model_path VARCHAR(255) DEFAULT NULL,

    -- adaptive / lockout tracking
    failed_password_attempts INT DEFAULT 0,   -- 0..5 (locks at 5)
    otp_resend_count INT DEFAULT 0,           -- 0..2 (locks on 3rd resend)
    failed_face_attempts INT DEFAULT 0,       -- 0..2 (locks at 2)
    is_locked BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_key VARCHAR(255) NOT NULL,        -- fresh session key generated per successful login
    signature TEXT NULL,                      -- Objective 2: Dilithium3 signature of session_key
    signature_algo VARCHAR(30) DEFAULT 'Dilithium3',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
