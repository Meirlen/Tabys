-- Migration: Add scheduling columns to news table
-- Run this SQL against your PostgreSQL database

-- Add status column (draft, scheduled, published)
ALTER TABLE news ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft' NOT NULL;

-- Add publish_at column (when to auto-publish)
ALTER TABLE news ADD COLUMN IF NOT EXISTS publish_at TIMESTAMP;

-- Add published_at column (actual publication time)
ALTER TABLE news ADD COLUMN IF NOT EXISTS published_at TIMESTAMP;

-- Add is_admin_created column (true if created by admin, bypasses moderation)
ALTER TABLE news ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT FALSE NOT NULL;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_news_status ON news(status);
CREATE INDEX IF NOT EXISTS ix_news_publish_at ON news(publish_at);

-- Update existing approved news to have 'published' status for backward compatibility
UPDATE news SET status = 'published', published_at = moderated_at
WHERE moderation_status = 'approved' AND status = 'draft';

-- Update existing pending/rejected news to remain as 'draft'
-- (they need moderation before scheduling)

SELECT 'Migration completed successfully!' as result;
