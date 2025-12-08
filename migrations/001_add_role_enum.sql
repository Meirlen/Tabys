-- Migration: Add Role Enum to Admin Table
-- This migration adds RBAC role support to the existing admin table

-- Step 1: Create the role enum type
CREATE TYPE roleenum AS ENUM (
    'client',
    'volunteer_admin',
    'msb',
    'npo',
    'government',
    'administrator',
    'super_admin'
);

-- Step 2: Add role column to admin table (if it doesn't exist with enum type)
-- Check if column exists first
DO $$
BEGIN
    -- Try to alter the column to use the enum
    BEGIN
        ALTER TABLE adminstrators_shaqyru1
        ALTER COLUMN role TYPE roleenum
        USING role::roleenum;
    EXCEPTION
        WHEN undefined_column THEN
            -- Column doesn't exist, add it
            ALTER TABLE adminstrators_shaqyru1
            ADD COLUMN role roleenum NOT NULL DEFAULT 'client';
        WHEN OTHERS THEN
            -- Column exists but wrong type, convert it
            ALTER TABLE adminstrators_shaqyru1
            ALTER COLUMN role TYPE roleenum
            USING CASE
                WHEN role = 'super_admin' THEN 'super_admin'::roleenum
                WHEN role = 'project_admin' THEN 'administrator'::roleenum
                ELSE 'client'::roleenum
            END;
    END;
END $$;

-- Step 3: Set default role for existing admins (adjust as needed)
UPDATE adminstrators_shaqyru1
SET role = 'super_admin'
WHERE role IS NULL OR role::text = '';

-- Step 4: Create index on role for faster queries
CREATE INDEX IF NOT EXISTS idx_admin_role ON adminstrators_shaqyru1(role);

-- Step 5: Add comment to document the column
COMMENT ON COLUMN adminstrators_shaqyru1.role IS 'User role for RBAC: client, volunteer_admin, msb, npo, government, administrator, super_admin';
