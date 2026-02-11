-- Fix PostgreSQL sequences that are out of sync
-- This happens when data is inserted with explicit IDs (like from seeding)

-- Fix login_history sequence
SELECT setval('login_history_id_seq', (SELECT MAX(id) FROM login_history) + 1);

-- Fix user_activities sequence (preventive)
SELECT setval('user_activities_id_seq', (SELECT MAX(id) FROM user_activities) + 1);

-- Fix system_events sequence (preventive)
SELECT setval('system_events_id_seq', (SELECT MAX(id) FROM system_events) + 1);

-- Fix users sequence (preventive)
SELECT setval('users_2026_12_id_seq', (SELECT MAX(id) FROM users_2026_12) + 1);

-- Show the results
SELECT 'login_history_id_seq' as sequence, currval('login_history_id_seq') as current_value
UNION ALL
SELECT 'user_activities_id_seq', currval('user_activities_id_seq')
UNION ALL
SELECT 'system_events_id_seq', currval('system_events_id_seq')
UNION ALL
SELECT 'users_2026_12_id_seq', currval('users_2026_12_id_seq');
