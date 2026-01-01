-- Rollback Migration: 001_add_news_view_count
-- Description: Remove view_count column from news table
-- Date: 2025-12-31

-- Drop index
DROP INDEX IF EXISTS idx_news_view_count;

-- Remove column
ALTER TABLE news
DROP COLUMN IF EXISTS view_count;
