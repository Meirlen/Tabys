-- Migration: Assign Initial Roles to Existing Admins
-- Customize this based on your existing admin users

-- Example: Assign roles based on login patterns or IDs

-- Set super admin for main admin account
UPDATE adminstrators_shaqyru1
SET role = 'super_admin'
WHERE login IN ('admin', 'superadmin', 'root');

-- Set volunteer admin for volunteer managers
UPDATE adminstrators_shaqyru1
SET role = 'volunteer_admin'
WHERE login LIKE '%volunteer%';

-- Set MSB role for business-related accounts
UPDATE adminstrators_shaqyru1
SET role = 'msb'
WHERE login LIKE '%msb%' OR login LIKE '%business%';

-- Set NPO role for non-profit organization accounts
UPDATE adminstrators_shaqyru1
SET role = 'npo'
WHERE login LIKE '%npo%' OR login LIKE '%ngo%';

-- Set government role for government accounts
UPDATE adminstrators_shaqyru1
SET role = 'government'
WHERE login LIKE '%gov%' OR login LIKE '%government%';

-- Set administrator role for general admins
UPDATE adminstrators_shaqyru1
SET role = 'administrator'
WHERE login LIKE '%admin%' AND role = 'client';

-- Verify role distribution
SELECT role, COUNT(*) as count
FROM adminstrators_shaqyru1
GROUP BY role
ORDER BY count DESC;

-- Show all admin accounts with their assigned roles
SELECT id, name, login, role, created_at
FROM adminstrators_shaqyru1
ORDER BY role, name;
