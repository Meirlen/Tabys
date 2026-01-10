-- Migration: Add email column to adminstrators_shaqyru1 table
-- Purpose: Enable email notifications for administrators
-- Date: 2026-01-10

-- Add email column to admins table
ALTER TABLE adminstrators_shaqyru1
ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Add comment to the column
COMMENT ON COLUMN adminstrators_shaqyru1.email IS 'Admin email address for notifications';

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_admins_email ON adminstrators_shaqyru1(email);

-- Optional: Update existing admin records with email if their login is already an email
-- This is a safe operation that only updates if the login looks like an email
UPDATE adminstrators_shaqyru1
SET email = login
WHERE email IS NULL
  AND login LIKE '%@%'
  AND login LIKE '%.%';
