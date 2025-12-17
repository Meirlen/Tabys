-- Add moderation columns to news table
ALTER TABLE news 
ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
ADD COLUMN IF NOT EXISTS source_url VARCHAR(1000),
ADD COLUMN IF NOT EXISTS source_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS language VARCHAR(10),
ADD COLUMN IF NOT EXISTS keywords_matched TEXT,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS moderated_by INTEGER;

-- Update existing records to have 'approved' status (so they show on public site)
UPDATE news SET moderation_status = 'approved' WHERE moderation_status IS NULL OR moderation_status = 'pending';
