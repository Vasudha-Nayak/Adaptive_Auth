-- Adaptive Login Mechanism - Database Schema
-- Run this once in MySQL to create the database and tables.

CREATE DATABASE IF NOT EXISTS adaptive_auth;
USE adaptive_auth;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    pattern_hash VARCHAR(255) NOT NULL,

    -- adaptive / lockout tracking
    failed_password_attempts INT DEFAULT 0,   -- 0..5 (locks at 5)
    otp_resend_count INT DEFAULT 0,           -- 0..2 (locks on 3rd resend)
    failed_pattern_attempts INT DEFAULT 0,    -- 0..2 (locks at 2)
    is_locked BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_key VARCHAR(255) NOT NULL,        -- fresh session key generated per successful login
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
