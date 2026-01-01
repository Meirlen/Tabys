-- Migration: 001_add_news_view_count
-- Description: Add view_count column to news table for tracking article views
-- Date: 2025-12-31
-- Author: System

-- Add view_count column to news table
ALTER TABLE news
ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0 NOT NULL;

-- Add index on view_count for faster sorting by popularity
CREATE INDEX IF NOT EXISTS idx_news_view_count ON news(view_count DESC);

-- Update existing records to have view_count = 0 (if column was just added)
UPDATE news
SET view_count = 0
WHERE view_count IS NULL;

-- Add comment to column for documentation
COMMENT ON COLUMN news.view_count IS 'Number of times the news article has been viewed by users';
