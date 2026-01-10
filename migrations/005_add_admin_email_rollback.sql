-- Rollback Migration: Remove email column from adminstrators_shaqyru1 table
-- Purpose: Revert email notifications feature
-- Date: 2026-01-10

-- Drop index first
DROP INDEX IF EXISTS idx_admins_email;

-- Remove email column
ALTER TABLE adminstrators_shaqyru1
DROP COLUMN IF EXISTS email;
