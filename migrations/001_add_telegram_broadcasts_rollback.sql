-- Rollback Migration: Remove Telegram Broadcasts Feature
-- Date: 2026-01-04
-- Description: Drops all tables and enums created for telegram broadcast messaging

-- ============================================================================
-- DROP TABLES (in reverse order of dependencies)
-- ============================================================================

DROP TABLE IF EXISTS telegram_broadcast_deliveries CASCADE;
DROP TABLE IF EXISTS telegram_broadcasts CASCADE;

-- ============================================================================
-- DROP ENUM TYPES
-- ============================================================================

DROP TYPE IF EXISTS delivery_status;
DROP TYPE IF EXISTS broadcast_status;
DROP TYPE IF EXISTS broadcast_target_audience;
