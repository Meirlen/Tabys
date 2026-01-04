-- Migration: Add Telegram Broadcast Tables
-- Description: Creates tables for broadcast messaging to Telegram bot users
-- Date: 2026-01-04
-- Author: System Migration

-- Create enum types for broadcasts
CREATE TYPE broadcast_target_audience AS ENUM (
    'all_telegram_users',
    'admins_only',
    'by_role',
    'active_sessions'
);

CREATE TYPE broadcast_status AS ENUM (
    'draft',
    'scheduled',
    'sending',
    'sent',
    'failed',
    'cancelled'
);

CREATE TYPE delivery_status AS ENUM (
    'pending',
    'sent',
    'delivered',
    'read',
    'failed'
);

-- Create telegram_broadcasts table
CREATE TABLE IF NOT EXISTS telegram_broadcasts (
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
    created_by INTEGER NOT NULL REFERENCES adminstrators_shaqyru1(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    scheduled_at TIMESTAMP WITHOUT TIME ZONE,
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

-- Create telegram_broadcast_deliveries table
CREATE TABLE IF NOT EXISTS telegram_broadcast_deliveries (
    id SERIAL PRIMARY KEY,
    broadcast_id INTEGER NOT NULL REFERENCES telegram_broadcasts(id) ON DELETE CASCADE,
    telegram_user_id VARCHAR(50) NOT NULL,
    
    -- Delivery status
    status delivery_status NOT NULL DEFAULT 'pending',
    
    -- Timestamps
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMP WITHOUT TIME ZONE,
    delivered_at TIMESTAMP WITHOUT TIME ZONE,
    read_at TIMESTAMP WITHOUT TIME ZONE,
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_broadcasts_created_by ON telegram_broadcasts(created_by);
CREATE INDEX IF NOT EXISTS idx_broadcasts_status ON telegram_broadcasts(status);
CREATE INDEX IF NOT EXISTS idx_broadcasts_created_at ON telegram_broadcasts(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deliveries_broadcast_id ON telegram_broadcast_deliveries(broadcast_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_telegram_user_id ON telegram_broadcast_deliveries(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON telegram_broadcast_deliveries(status);

-- Add comments for documentation
COMMENT ON TABLE telegram_broadcasts IS 'Telegram broadcast messages sent to bot users';
COMMENT ON TABLE telegram_broadcast_deliveries IS 'Individual delivery tracking for broadcast messages';
COMMENT ON COLUMN telegram_broadcasts.target_audience IS 'Target audience filter for broadcast';
COMMENT ON COLUMN telegram_broadcasts.target_role IS 'Specific role filter when target_audience is BY_ROLE';
