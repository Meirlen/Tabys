-- ROLLBACK Migration: Remove admin_id columns
-- Date: 2026-01-06
-- Description: Rollback script to remove admin_id columns if needed
-- WARNING: This will drop the admin_id columns and their indexes!

-- ============================================================================
-- DROP INDEXES
-- ============================================================================
DROP INDEX IF EXISTS idx_vacancies_new_2025_admin_id;
DROP INDEX IF EXISTS idx_events_admin_id;
DROP INDEX IF EXISTS idx_projects_multi_2_admin_id;
DROP INDEX IF EXISTS idx_tickets_admin_id;
DROP INDEX IF EXISTS idx_places_admin_id;
DROP INDEX IF EXISTS idx_promo_actions_admin_id;
DROP INDEX IF EXISTS idx_telegram_otp_tokens_admin_id;
DROP INDEX IF EXISTS idx_telegram_sessions_admin_id;


-- ============================================================================
-- DROP COLUMNS
-- ============================================================================
ALTER TABLE vacancies_new_2025_ DROP COLUMN IF EXISTS admin_id;
ALTER TABLE events_ DROP COLUMN IF EXISTS admin_id;
ALTER TABLE projects_multi_2 DROP COLUMN IF EXISTS admin_id;
ALTER TABLE tickets DROP COLUMN IF EXISTS admin_id;
ALTER TABLE places DROP COLUMN IF EXISTS admin_id;
ALTER TABLE promo_actions DROP COLUMN IF EXISTS admin_id;

-- Telegram tables (conditionally)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.columns
              WHERE table_name = 'telegram_otp_tokens' AND column_name = 'admin_id') THEN
        ALTER TABLE telegram_otp_tokens DROP COLUMN admin_id;
    END IF;

    IF EXISTS (SELECT FROM information_schema.columns
              WHERE table_name = 'telegram_sessions' AND column_name = 'admin_id') THEN
        ALTER TABLE telegram_sessions DROP COLUMN admin_id;
    END IF;
END $$;

-- Analytics tables
ALTER TABLE user_activities DROP COLUMN IF EXISTS admin_id;
ALTER TABLE login_history DROP COLUMN IF EXISTS admin_id;
ALTER TABLE system_events DROP COLUMN IF EXISTS admin_id;


-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Verify columns are removed
SELECT
    table_name,
    column_name
FROM information_schema.columns
WHERE column_name = 'admin_id'
  AND table_schema = 'public'
ORDER BY table_name;

-- Should return no results if rollback was successful
