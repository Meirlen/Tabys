-- Rollback: Remove approval status fields from adminstrators_shaqyru1 table
-- Date: 2026-01-03

-- Drop index
DROP INDEX IF EXISTS idx_admin_approval_status;

-- Remove columns
ALTER TABLE adminstrators_shaqyru1 DROP COLUMN IF EXISTS approval_status;
ALTER TABLE adminstrators_shaqyru1 DROP COLUMN IF EXISTS approval_reason;
ALTER TABLE adminstrators_shaqyru1 DROP COLUMN IF EXISTS approved_at;
ALTER TABLE adminstrators_shaqyru1 DROP COLUMN IF EXISTS approved_by;
