-- Migration: Add multi-language support to news table
-- Date: 2025-12-01
-- Description: Adds Kazakh and Russian language fields to news table without breaking existing data

-- Add Kazakh language fields
ALTER TABLE news ADD COLUMN IF NOT EXISTS title_kz VARCHAR(255) DEFAULT NULL;
ALTER TABLE news ADD COLUMN IF NOT EXISTS description_kz TEXT DEFAULT NULL;
ALTER TABLE news ADD COLUMN IF NOT EXISTS content_text_kz TEXT DEFAULT NULL;

-- Add Russian language fields
ALTER TABLE news ADD COLUMN IF NOT EXISTS title_ru VARCHAR(255) DEFAULT NULL;
ALTER TABLE news ADD COLUMN IF NOT EXISTS description_ru TEXT DEFAULT NULL;
ALTER TABLE news ADD COLUMN IF NOT EXISTS content_text_ru TEXT DEFAULT NULL;

-- Make original fields nullable (for backward compatibility)
ALTER TABLE news ALTER COLUMN title DROP NOT NULL;
ALTER TABLE news ALTER COLUMN description DROP NOT NULL;
ALTER TABLE news ALTER COLUMN content_text DROP NOT NULL;

-- Optional: Migrate existing data to Russian fields (if existing news are in Russian)
-- Uncomment the following lines if you want to copy existing data to title_ru, description_ru, content_text_ru
-- UPDATE news SET title_ru = title WHERE title_ru IS NULL AND title IS NOT NULL;
-- UPDATE news SET description_ru = description WHERE description_ru IS NULL AND description IS NOT NULL;
-- UPDATE news SET content_text_ru = content_text WHERE content_text_ru IS NULL AND content_text IS NOT NULL;

-- Create indexes for better query performance on language fields
CREATE INDEX IF NOT EXISTS idx_news_title_kz ON news(title_kz);
CREATE INDEX IF NOT EXISTS idx_news_title_ru ON news(title_ru);
