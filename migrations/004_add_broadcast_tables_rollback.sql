-- Rollback Migration: Remove Telegram Broadcast Tables
-- Description: Drops broadcast tables and enum types
-- Date: 2026-01-04

-- Drop tables (cascade will remove foreign key constraints)
DROP TABLE IF EXISTS telegram_broadcast_deliveries CASCADE;
DROP TABLE IF EXISTS telegram_broadcasts CASCADE;

-- Drop enum types
DROP TYPE IF EXISTS delivery_status CASCADE;
DROP TYPE IF EXISTS broadcast_status CASCADE;
DROP TYPE IF EXISTS broadcast_target_audience CASCADE;
