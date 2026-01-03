-- Migration: Add approval status fields to adminstrators_shaqyru1 table
-- Date: 2026-01-03
-- Description: Adds approval workflow for admin registrations

-- Add approval_status column (pending, approved, rejected)
-- Default is 'approved' for existing admins
ALTER TABLE adminstrators_shaqyru1
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'approved' NOT NULL;

-- Add approval_reason column for optional comments from superadmin
ALTER TABLE adminstrators_shaqyru1
ADD COLUMN IF NOT EXISTS approval_reason TEXT;

-- Add approved_at timestamp
ALTER TABLE adminstrators_shaqyru1
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;

-- Add approved_by to track which superadmin approved/rejected
ALTER TABLE adminstrators_shaqyru1
ADD COLUMN IF NOT EXISTS approved_by INTEGER;

-- Create index for faster queries on pending registrations
CREATE INDEX IF NOT EXISTS idx_admin_approval_status
ON adminstrators_shaqyru1(approval_status);

-- Add comment to table
COMMENT ON COLUMN adminstrators_shaqyru1.approval_status IS 'Registration status: pending, approved, rejected';
COMMENT ON COLUMN adminstrators_shaqyru1.approval_reason IS 'Optional reason for approval/rejection decision';
COMMENT ON COLUMN adminstrators_shaqyru1.approved_at IS 'Timestamp when the registration was approved/rejected';
COMMENT ON COLUMN adminstrators_shaqyru1.approved_by IS 'ID of the superadmin who approved/rejected the registration';
