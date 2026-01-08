-- =====================================================
-- MODERATION SYSTEM DATABASE MIGRATIONS
-- Add moderation fields to all content entities
-- Run this BEFORE modifying Python models
-- =====================================================

-- =====================================================
-- 1. EVENTS TABLE
-- =====================================================
ALTER TABLE events_
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_events_moderation_status ON events_(moderation_status);

COMMENT ON COLUMN events_.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN events_.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN events_.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN events_.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- 2. VACANCIES TABLE
-- =====================================================
ALTER TABLE vacancies_new_2025_
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vacancies_moderation_status ON vacancies_new_2025_(moderation_status);

COMMENT ON COLUMN vacancies_new_2025_.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN vacancies_new_2025_.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN vacancies_new_2025_.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN vacancies_new_2025_.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- 3. COURSES TABLE
-- =====================================================
ALTER TABLE courses
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_courses_moderation_status ON courses(moderation_status);

COMMENT ON COLUMN courses.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN courses.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN courses.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN courses.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- 4. PROJECTS TABLE
-- =====================================================
ALTER TABLE projects_multi_2
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_projects_moderation_status ON projects_multi_2(moderation_status);

COMMENT ON COLUMN projects_multi_2.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN projects_multi_2.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN projects_multi_2.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN projects_multi_2.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- 5. LEISURE - PLACES TABLE
-- =====================================================
ALTER TABLE places
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_places_moderation_status ON places(moderation_status);

COMMENT ON COLUMN places.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN places.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN places.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN places.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- 6. LEISURE - TICKETS TABLE
-- =====================================================
ALTER TABLE tickets
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tickets_moderation_status ON tickets(moderation_status);

COMMENT ON COLUMN tickets.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN tickets.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN tickets.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN tickets.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- 7. LEISURE - PROMO ACTIONS TABLE
-- =====================================================
ALTER TABLE promo_actions
  ADD COLUMN IF NOT EXISTS moderation_status VARCHAR(20) DEFAULT 'approved' NOT NULL,
  ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS moderated_by INTEGER,
  ADD COLUMN IF NOT EXISTS moderation_comment TEXT,
  ADD COLUMN IF NOT EXISTS is_admin_created BOOLEAN DEFAULT TRUE NOT NULL;

CREATE INDEX IF NOT EXISTS idx_promo_actions_moderation_status ON promo_actions(moderation_status);

COMMENT ON COLUMN promo_actions.moderation_status IS 'Moderation status: pending, approved, rejected';
COMMENT ON COLUMN promo_actions.moderated_at IS 'Timestamp when moderation action was taken';
COMMENT ON COLUMN promo_actions.moderated_by IS 'Admin ID who performed moderation';
COMMENT ON COLUMN promo_actions.is_admin_created IS 'True if created by administrator/super_admin (auto-approved)';


-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================
-- Run these to verify migrations succeeded

SELECT 'events_' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM events_

UNION ALL

SELECT 'vacancies_new_2025_' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM vacancies_new_2025_

UNION ALL

SELECT 'courses' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM courses

UNION ALL

SELECT 'projects_multi_2' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM projects_multi_2

UNION ALL

SELECT 'places' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM places

UNION ALL

SELECT 'tickets' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM tickets

UNION ALL

SELECT 'promo_actions' AS table_name,
       COUNT(*) AS total_rows,
       COUNT(CASE WHEN moderation_status = 'approved' THEN 1 END) AS approved_count
FROM promo_actions;


-- =====================================================
-- END OF MIGRATIONS
-- =====================================================
