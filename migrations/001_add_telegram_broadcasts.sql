-- Migration: Add Telegram Broadcasts Feature
-- Date: 2026-01-04
-- Description: Creates tables and enums for telegram broadcast messaging system

-- ============================================================================
-- CREATE ENUM TYPES
-- ============================================================================

-- Target audience types for broadcasts
CREATE TYPE broadcast_target_audience AS ENUM (
    'all_telegram_users',
    'admins_only',
    'by_role',
    'active_sessions'
);

-- Broadcast status types
CREATE TYPE broadcast_status AS ENUM (
    'draft',
    'scheduled',
    'sending',
    'sent',
    'failed',
    'cancelled'
);

-- Individual delivery status types
CREATE TYPE delivery_status AS ENUM (
    'pending',
    'sent',
    'delivered',
    'read',
    'failed'
);

-- ============================================================================
-- CREATE TABLES
-- ============================================================================

-- Main broadcasts table
CREATE TABLE telegram_broadcasts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Targeting
    target_audience broadcast_target_audience NOT NULL DEFAULT 'all_telegram_users',
    target_role VARCHAR(50),

    -- Status tracking
    status broadcast_status NOT NULL DEFAULT 'draft',

    -- Statistics
    total_recipients INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    delivered_count INTEGER DEFAULT 0,
    read_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,

    -- Metadata
    created_by INTEGER NOT NULL REFERENCES adminstrators_shaqyru1(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scheduled_at TIMESTAMP,
    sent_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Individual broadcast delivery tracking table
CREATE TABLE telegram_broadcast_deliveries (
    id SERIAL PRIMARY KEY,
    broadcast_id INTEGER NOT NULL REFERENCES telegram_broadcasts(id) ON DELETE CASCADE,
    telegram_user_id VARCHAR(50) NOT NULL,

    -- Delivery status
    status delivery_status NOT NULL DEFAULT 'pending',

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,

    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- ============================================================================
-- CREATE INDEXES
-- ============================================================================

-- Index for faster lookups by telegram user
CREATE INDEX idx_broadcast_deliveries_telegram_user
    ON telegram_broadcast_deliveries(telegram_user_id);

-- Index for faster lookups by broadcast
CREATE INDEX idx_broadcast_deliveries_broadcast
    ON telegram_broadcast_deliveries(broadcast_id);

-- Index for faster status queries
CREATE INDEX idx_broadcast_deliveries_status
    ON telegram_broadcast_deliveries(status);

-- Index for faster broadcast status queries
CREATE INDEX idx_broadcasts_status
    ON telegram_broadcasts(status);

-- Index for faster broadcast creation time queries
CREATE INDEX idx_broadcasts_created_at
    ON telegram_broadcasts(created_at DESC);

-- Index for faster creator queries
CREATE INDEX idx_broadcasts_created_by
    ON telegram_broadcasts(created_by);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE telegram_broadcasts IS 'Stores telegram broadcast messages sent to bot users';
COMMENT ON TABLE telegram_broadcast_deliveries IS 'Tracks individual message delivery status for each broadcast';

COMMENT ON COLUMN telegram_broadcasts.target_audience IS 'Defines which users should receive this broadcast';
COMMENT ON COLUMN telegram_broadcasts.target_role IS 'Specific role filter when target_audience is by_role';
COMMENT ON COLUMN telegram_broadcasts.status IS 'Current status of the broadcast';
COMMENT ON COLUMN telegram_broadcasts.total_recipients IS 'Total number of users who should receive this broadcast';
COMMENT ON COLUMN telegram_broadcasts.sent_count IS 'Number of messages successfully sent';
COMMENT ON COLUMN telegram_broadcasts.delivered_count IS 'Number of messages delivered to users';
COMMENT ON COLUMN telegram_broadcasts.read_count IS 'Number of messages marked as read by users';
COMMENT ON COLUMN telegram_broadcasts.failed_count IS 'Number of failed delivery attempts';

COMMENT ON COLUMN telegram_broadcast_deliveries.telegram_user_id IS 'Telegram user ID of the recipient';
COMMENT ON COLUMN telegram_broadcast_deliveries.status IS 'Delivery status for this specific user';
COMMENT ON COLUMN telegram_broadcast_deliveries.error_message IS 'Error message if delivery failed';
COMMENT ON COLUMN telegram_broadcast_deliveries.retry_count IS 'Number of retry attempts for failed deliveries';
