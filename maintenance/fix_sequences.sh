#!/bin/bash

# Quick fix script for PostgreSQL sequence issues
# Usage: ./fix_sequences.sh

echo "Fixing all PostgreSQL sequences..."

docker exec -i tabys-postgres-1 psql -U postgres -d alem << SQL
-- Reset all sequences to match their table data
DO \$\$
DECLARE
    seq_record RECORD;
    table_name TEXT;
    max_id INTEGER;
BEGIN
    FOR seq_record IN 
        SELECT sequence_name 
        FROM information_schema.sequences 
        WHERE sequence_schema = 'public' 
        AND sequence_name LIKE '%_id_seq'
    LOOP
        -- Extract table name from sequence name
        table_name := REPLACE(seq_record.sequence_name, '_id_seq', '');
        
        -- Check if table exists
        IF EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = table_name
        ) THEN
            -- Get max ID from table
            EXECUTE format('SELECT COALESCE(MAX(id), 0) FROM %I', table_name) INTO max_id;
            
            -- Reset sequence
            EXECUTE format('SELECT setval(%L, %s, true)', seq_record.sequence_name, max_id);
            
            RAISE NOTICE 'Fixed % (set to %)', seq_record.sequence_name, max_id;
        END IF;
    END LOOP;
END \$\$;
SQL

echo "✓ All sequences fixed!"
