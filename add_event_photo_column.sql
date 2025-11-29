-- SQL script to add event_photo column to existing events_ table
-- Run this if the backend is already running with existing data

-- Add the event_photo column to the events_ table
ALTER TABLE events_ ADD COLUMN IF NOT EXISTS event_photo VARCHAR;

-- Verify the column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'events_'
ORDER BY ordinal_position;
