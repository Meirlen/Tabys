-- Migration: Add category column to news table
-- Date: 2025-11-30
-- Description: Adds an optional category field to the news table for categorizing news articles

-- Add category column (nullable for backward compatibility)
ALTER TABLE news ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT NULL;

-- Create index on category for better query performance
CREATE INDEX IF NOT EXISTS idx_news_category ON news(category);

-- Optional: Add some sample categories to existing news (commented out by default)
-- UPDATE news SET category = 'Общие' WHERE category IS NULL;
