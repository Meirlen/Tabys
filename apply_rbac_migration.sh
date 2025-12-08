#!/bin/bash

# RBAC Migration Script
# This script applies the RBAC database migration to your PostgreSQL database

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║            RBAC Database Migration Script                          ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get database connection details
echo -e "${YELLOW}Please provide your database connection details:${NC}"
echo ""

read -p "Database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Database port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Database name: " DB_NAME
if [ -z "$DB_NAME" ]; then
    echo -e "${RED}Database name is required!${NC}"
    exit 1
fi

read -p "Database user [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -sp "Database password: " DB_PASSWORD
echo ""

# Test connection
echo ""
echo -e "${YELLOW}Testing database connection...${NC}"
export PGPASSWORD="$DB_PASSWORD"

if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
    echo -e "${GREEN}✓ Connection successful!${NC}"
else
    echo -e "${RED}✗ Connection failed. Please check your credentials.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 1: Creating role enum type${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Check if enum already exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'roleenum') THEN
        CREATE TYPE roleenum AS ENUM (
            'client',
            'volunteer_admin',
            'msb',
            'npo',
            'government',
            'administrator',
            'super_admin'
        );
        RAISE NOTICE '✓ Role enum type created successfully';
    ELSE
        RAISE NOTICE '✓ Role enum type already exists';
    END IF;
END $$;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Enum type ready${NC}"
else
    echo -e "${RED}✗ Failed to create enum type${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 2: Checking current role column${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'adminstrators_shaqyru1'
AND column_name = 'role';
EOF

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 3: Updating existing roles to valid values${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Set NULL or empty roles to 'super_admin' (for safety, existing admins get full access)
UPDATE adminstrators_shaqyru1
SET role = 'super_admin'
WHERE role IS NULL OR role = '' OR role NOT IN (
    'client', 'volunteer_admin', 'msb', 'npo',
    'government', 'administrator', 'super_admin'
);

-- Map old 'project_admin' role to 'administrator' if exists
UPDATE adminstrators_shaqyru1
SET role = 'administrator'
WHERE role = 'project_admin';

-- Show updated roles
SELECT role, COUNT(*) as count
FROM adminstrators_shaqyru1
GROUP BY role
ORDER BY count DESC;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Roles updated${NC}"
else
    echo -e "${RED}✗ Failed to update roles${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 4: Converting role column to enum (if needed)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
DO $$
DECLARE
    current_type text;
BEGIN
    -- Get current data type
    SELECT data_type INTO current_type
    FROM information_schema.columns
    WHERE table_name = 'adminstrators_shaqyru1'
    AND column_name = 'role';

    -- Only convert if not already enum
    IF current_type != 'USER-DEFINED' THEN
        ALTER TABLE adminstrators_shaqyru1
        ALTER COLUMN role TYPE roleenum
        USING role::roleenum;

        RAISE NOTICE '✓ Column converted to enum type';
    ELSE
        RAISE NOTICE '✓ Column already uses enum type';
    END IF;
END $$;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Column type updated${NC}"
else
    echo -e "${RED}✗ Failed to update column type${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 5: Creating index on role column${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
CREATE INDEX IF NOT EXISTS idx_admin_role ON adminstrators_shaqyru1(role);
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Index created${NC}"
else
    echo -e "${RED}✗ Failed to create index${NC}"
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Step 6: Verifying migration${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
-- Show all admins with their roles
SELECT
    id,
    name,
    login,
    role,
    created_at
FROM adminstrators_shaqyru1
ORDER BY role, name;

-- Show role distribution
SELECT
    role,
    COUNT(*) as admin_count
FROM adminstrators_shaqyru1
GROUP BY role
ORDER BY admin_count DESC;
EOF

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  ✓ MIGRATION COMPLETED SUCCESSFULLY                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart your FastAPI backend"
echo "2. Test the RBAC system with different user roles"
echo "3. Check the documentation in START_HERE.md"
echo ""
echo -e "${GREEN}Done!${NC}"
