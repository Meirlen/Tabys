-- =============================================================================
-- CLEANUP FAKE SEED USERS
-- =============================================================================
-- Removes all users and organizations inserted by seed_analytics.py.
--
-- Identification criteria (all patterns come from seed_analytics.py):
--
--   1. Phone number starts with '+77'            (seed format — real users use '77...' without '+')
--   2. Individual.full_name in SAMPLE_NAMES_RU   (15 hardcoded Russian transliterations)
--   3. Individual.id_document_photo like '/uploads/ids/id_%.jpg'
--   4. Individual.selfie_with_id_photo  like '/uploads/selfies/selfie_%.jpg'
--   5. Individual.address               like 'г. Астана, ул. Независимости%'
--   6. Organization.name in ORG_NAMES            (9 hardcoded fake org names)
--   7. Organization.email               like 'info%@company.kz'
--   8. Organization.address             like 'г. Алматы, пр. Абая%'
--
-- Deletion order respects all foreign-key constraints found in the schema.
-- The script is wrapped in a transaction so it can be rolled back if needed.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Collect fake user IDs into a temporary table
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _fake_user_ids AS
SELECT DISTINCT u.id
FROM users_ u
WHERE
    -- Seed phone format: +77XXXXXXXXX  (real users registered as 77...)
    u.phone_number LIKE '+77%'

    -- Individuals: fake names from SAMPLE_NAMES_RU
    OR u.id IN (
        SELECT user_id FROM individuals
        WHERE full_name IN (
            'Айдос Нурланов',
            'Жанар Сабитова',
            'Асель Канатова',
            'Ерлан Болатов',
            'Динара Алмасова',
            'Арман Ержанов',
            'Гульнур Даулетова',
            'Бекзат Нурболов',
            'Айгерим Сериков',
            'Данияр Муратов',
            'Самал Акжолова',
            'Нурлан Ганиев',
            'Айым Темирова',
            'Бауыржан Жаксылыков',
            'Сауле Асемова'
        )
    )

    -- Individuals: fake document-photo paths  (/uploads/ids/id_N.jpg)
    OR u.id IN (
        SELECT user_id FROM individuals
        WHERE id_document_photo     LIKE '/uploads/ids/id_%.jpg'
           OR selfie_with_id_photo  LIKE '/uploads/selfies/selfie_%.jpg'
           OR address               LIKE 'г. Астана, ул. Независимости%'
    )

    -- Organizations: fake names from ORG_NAMES
    OR u.id IN (
        SELECT user_id FROM organizations
        WHERE name IN (
            'ТОО ''Сарыарқа Даму''',
            'ЖШС ''Нұр Технология''',
            'АО ''Қазақстан Инновация''',
            'ТОО ''Жастар Орталығы''',
            'ЖШС ''Алтын Білім''',
            'АО ''Астана Цифр''',
            'ТОО ''Қызылорда Спорт''',
            'ЖШС ''Атырау Мәдениет''',
            'АО ''Ақтөбе Жастар'''
        )
    )

    -- Organizations: fake email / address patterns
    OR u.id IN (
        SELECT user_id FROM organizations
        WHERE email   LIKE 'info%@company.kz'
           OR address LIKE 'г. Алматы, пр. Абая%'
    );

-- Show how many users will be removed (helpful for verification)
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt FROM _fake_user_ids;
    RAISE NOTICE 'Fake seed users identified: %', cnt;
END $$;

-- ---------------------------------------------------------------------------
-- 2. Delete child records before deleting users
--    (follow FK dependency order)
-- ---------------------------------------------------------------------------

-- 2a. Course progress / test results reference course_enrollments
DELETE FROM course_lesson_progress
WHERE enrollment_id IN (
    SELECT id FROM course_enrollments
    WHERE user_id IN (SELECT id FROM _fake_user_ids)
);

DELETE FROM course_test_results
WHERE enrollment_id IN (
    SELECT id FROM course_enrollments
    WHERE user_id IN (SELECT id FROM _fake_user_ids)
);

-- 2b. Analytics tables
DELETE FROM user_activities    WHERE user_id IN (SELECT id FROM _fake_user_ids);
DELETE FROM login_history      WHERE user_id IN (SELECT id FROM _fake_user_ids);
DELETE FROM system_events      WHERE user_id IN (SELECT id FROM _fake_user_ids);
DELETE FROM user_sessions      WHERE user_id IN (SELECT id FROM _fake_user_ids);

-- 2c. Submissions and applications
DELETE FROM project_form_submissions  WHERE user_id IN (SELECT id FROM _fake_user_ids);
DELETE FROM vacancy_applications_v2   WHERE user_id IN (SELECT id FROM _fake_user_ids);
DELETE FROM votes_                    WHERE user_id IN (SELECT id FROM _fake_user_ids);

-- 2d. Resume child tables (reference resumes_.id)
DELETE FROM resume_education
WHERE resume_id IN (
    SELECT id FROM resumes_ WHERE user_id IN (SELECT id FROM _fake_user_ids)
);

DELETE FROM resume_skills
WHERE resume_id IN (
    SELECT id FROM resumes_ WHERE user_id IN (SELECT id FROM _fake_user_ids)
);

DELETE FROM resume_work_experience
WHERE resume_id IN (
    SELECT id FROM resumes_ WHERE user_id IN (SELECT id FROM _fake_user_ids)
);

-- 2e. Resumes
DELETE FROM resumes_ WHERE user_id IN (SELECT id FROM _fake_user_ids);

-- 2f. Course enrollments
DELETE FROM course_enrollments WHERE user_id IN (SELECT id FROM _fake_user_ids);

-- 2g. Volunteers
DELETE FROM volunteers_ WHERE user_id IN (SELECT id FROM _fake_user_ids);

-- ---------------------------------------------------------------------------
-- 3. Delete profiles (individuals / organizations)
-- ---------------------------------------------------------------------------
DELETE FROM individuals   WHERE user_id IN (SELECT id FROM _fake_user_ids);
DELETE FROM organizations WHERE user_id IN (SELECT id FROM _fake_user_ids);

-- ---------------------------------------------------------------------------
-- 4. Delete the users themselves
-- ---------------------------------------------------------------------------
DELETE FROM users_ WHERE id IN (SELECT id FROM _fake_user_ids);

-- ---------------------------------------------------------------------------
-- 5. Cleanup
-- ---------------------------------------------------------------------------
DROP TABLE _fake_user_ids;

-- Verify remaining users
DO $$
DECLARE
    remaining INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining FROM users_;
    RAISE NOTICE 'Users remaining after cleanup: %', remaining;
END $$;

COMMIT;
