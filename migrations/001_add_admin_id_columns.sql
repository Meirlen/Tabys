-- Migration: Add admin_id columns for RBAC ownership tracking
-- Date: 2026-01-06
-- Description: Adds admin_id columns to various tables to support role-based access control
--              where MSB and NPO users only see their own content

-- ============================================================================
-- VACANCIES TABLE
-- ============================================================================
-- Add admin_id column to vacancies_new_2025_
ALTER TABLE vacancies_new_2025_
ADD COLUMN IF NOT EXISTS admin_id INTEGER REFERENCES adminstrators_shaqyru1(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_vacancies_new_2025_admin_id
ON vacancies_new_2025_(admin_id);

COMMENT ON COLUMN vacancies_new_2025_.admin_id IS 'Admin who created this vacancy - used for RBAC filtering';


-- ============================================================================
-- EVENTS TABLE
-- ============================================================================
-- Add admin_id column to events_
ALTER TABLE events_
ADD COLUMN IF NOT EXISTS admin_id INTEGER REFERENCES adminstrators_shaqyru1(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_events_admin_id
ON events_(admin_id);

COMMENT ON COLUMN events_.admin_id IS 'Admin who created this event - used for RBAC filtering';


-- ============================================================================
-- PROJECTS TABLE
-- ============================================================================
-- Add admin_id column to projects_multi_2
ALTER TABLE projects_multi_2
ADD COLUMN IF NOT EXISTS admin_id INTEGER REFERENCES adminstrators_shaqyru1(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_projects_multi_2_admin_id
ON projects_multi_2(admin_id);

-- Migrate data from old creator_id column to new admin_id column
UPDATE projects_multi_2
SET admin_id = creator_id
WHERE admin_id IS NULL AND creator_id IS NOT NULL;

COMMENT ON COLUMN projects_multi_2.admin_id IS 'Admin who created this project - used for RBAC filtering';


-- ============================================================================
-- LEISURE TABLES
-- ============================================================================
-- Add admin_id to tickets table
ALTER TABLE tickets
ADD COLUMN IF NOT EXISTS admin_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_tickets_admin_id
ON tickets(admin_id);

COMMENT ON COLUMN tickets.admin_id IS 'Admin who created this ticket - used for RBAC filtering';


-- Add admin_id to places table
ALTER TABLE places
ADD COLUMN IF NOT EXISTS admin_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_places_admin_id
ON places(admin_id);

COMMENT ON COLUMN places.admin_id IS 'Admin who created this place - used for RBAC filtering';


-- Add admin_id to promo_actions table
ALTER TABLE promo_actions
ADD COLUMN IF NOT EXISTS admin_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_promo_actions_admin_id
ON promo_actions(admin_id);

COMMENT ON COLUMN promo_actions.admin_id IS 'Admin who created this promo - used for RBAC filtering';


-- ============================================================================
-- TELEGRAM TABLES
-- ============================================================================
-- Note: These tables may not exist yet, so we use a DO block to check first

DO $$
BEGIN
    -- telegram_otp_tokens
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'telegram_otp_tokens') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'telegram_otp_tokens' AND column_name = 'admin_id') THEN
            -- Check if table has data
            IF (SELECT COUNT(*) FROM telegram_otp_tokens) = 0 THEN
                ALTER TABLE telegram_otp_tokens
                ADD COLUMN admin_id INTEGER NOT NULL REFERENCES adminstrators_shaqyru1(id);
            ELSE
                -- Has data, add as nullable first
                ALTER TABLE telegram_otp_tokens
                ADD COLUMN admin_id INTEGER REFERENCES adminstrators_shaqyru1(id);
            END IF;

            CREATE INDEX IF NOT EXISTS idx_telegram_otp_tokens_admin_id
            ON telegram_otp_tokens(admin_id);
        END IF;
    END IF;

    -- telegram_sessions
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'telegram_sessions') THEN
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'telegram_sessions' AND column_name = 'admin_id') THEN
            IF (SELECT COUNT(*) FROM telegram_sessions) = 0 THEN
                ALTER TABLE telegram_sessions
                ADD COLUMN admin_id INTEGER NOT NULL REFERENCES adminstrators_shaqyru1(id);
            ELSE
                ALTER TABLE telegram_sessions
                ADD COLUMN admin_id INTEGER REFERENCES adminstrators_shaqyru1(id);
            END IF;

            CREATE INDEX IF NOT EXISTS idx_telegram_sessions_admin_id
            ON telegram_sessions(admin_id);
        END IF;
    END IF;
END $$;


-- ============================================================================
-- ANALYTICS TABLES (already have admin_id, but adding for completeness)
-- ============================================================================
ALTER TABLE user_activities
ADD COLUMN IF NOT EXISTS admin_id INTEGER;

ALTER TABLE login_history
ADD COLUMN IF NOT EXISTS admin_id INTEGER;

ALTER TABLE system_events
ADD COLUMN IF NOT EXISTS admin_id INTEGER;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these queries to verify the migration was successful:

-- Check all admin_id columns exist
SELECT
    c.table_name,
    c.column_name,
    c.is_nullable,
    c.data_type,
    CASE
        WHEN kcu.constraint_name IS NOT NULL THEN 'YES'
        ELSE 'NO'
    END as has_foreign_key
FROM information_schema.columns c
LEFT JOIN information_schema.key_column_usage kcu
    ON c.table_name = kcu.table_name
    AND c.column_name = kcu.column_name
    AND kcu.constraint_name LIKE '%fkey'
WHERE c.column_name = 'admin_id'
  AND c.table_schema = 'public'
ORDER BY c.table_name;

-- Check all indexes exist
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE '%admin_id%'
ORDER BY tablename;

-- Show sample data (should show NULL for existing records)
SELECT 'vacancies_new_2025_' as table_name, COUNT(*) as total, COUNT(admin_id) as with_admin_id FROM vacancies_new_2025_
UNION ALL
SELECT 'events_', COUNT(*), COUNT(admin_id) FROM events_
UNION ALL
SELECT 'projects_multi_2', COUNT(*), COUNT(admin_id) FROM projects_multi_2
UNION ALL
SELECT 'tickets', COUNT(*), COUNT(admin_id) FROM tickets
UNION ALL
SELECT 'places', COUNT(*), COUNT(admin_id) FROM places
UNION ALL
SELECT 'promo_actions', COUNT(*), COUNT(admin_id) FROM promo_actions;
