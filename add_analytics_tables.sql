-- Create analytics tables for user activity tracking

-- User Activities Table
CREATE TABLE IF NOT EXISTS user_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    admin_id INTEGER,
    user_type VARCHAR(20) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    description TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_admin_id ON user_activities(admin_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_user_type ON user_activities(user_type);
CREATE INDEX IF NOT EXISTS idx_user_activities_action_type ON user_activities(action_type);
CREATE INDEX IF NOT EXISTS idx_user_activities_resource_type ON user_activities(resource_type);
CREATE INDEX IF NOT EXISTS idx_user_activities_created_at ON user_activities(created_at DESC);

-- Login History Table
CREATE TABLE IF NOT EXISTS login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    admin_id INTEGER,
    user_type VARCHAR(20) NOT NULL,
    phone_number VARCHAR(20),
    login VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    failure_reason VARCHAR(200),
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for login history
CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_admin_id ON login_history(admin_id);
CREATE INDEX IF NOT EXISTS idx_login_history_status ON login_history(status);
CREATE INDEX IF NOT EXISTS idx_login_history_created_at ON login_history(created_at DESC);

-- System Events Table
CREATE TABLE IF NOT EXISTS system_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    source VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    user_id INTEGER,
    admin_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes for system events
CREATE INDEX IF NOT EXISTS idx_system_events_event_type ON system_events(event_type);
CREATE INDEX IF NOT EXISTS idx_system_events_source ON system_events(source);
CREATE INDEX IF NOT EXISTS idx_system_events_created_at ON system_events(created_at DESC);

-- Verify tables were created
\dt user_activities
\dt login_history
\dt system_events
