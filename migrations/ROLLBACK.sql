-- Rollback: Remove RBAC role enum if needed
-- WARNING: This will remove all role data!

-- Step 1: Drop the index
DROP INDEX IF EXISTS idx_admin_role;

-- Step 2: Convert role column back to string (if you want to keep data)
ALTER TABLE adminstrators_shaqyru1
ALTER COLUMN role TYPE VARCHAR(50)
USING role::text;

-- Step 3: Drop the enum type
DROP TYPE IF EXISTS roleenum;

-- Alternative: Just drop the column entirely
-- ALTER TABLE adminstrators_shaqyru1 DROP COLUMN IF EXISTS role;
