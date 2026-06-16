-- Схема wvs в базе communication (одинаково на stage и prod).
-- Каждый сервис — отдельная схема по этому шаблону (users, events).
--
-- Ручная установка:
--   psql -h localhost -U roman -d communication -f sql/001_init.sql

CREATE SCHEMA IF NOT EXISTS wvs;

CREATE TABLE IF NOT EXISTS wvs.users (
    user_id TEXT PRIMARY KEY,
    internal_user_id BIGSERIAL NOT NULL UNIQUE,
    external_user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    registration_date TIMESTAMP NOT NULL,
    registration_channel TEXT NOT NULL,
    last_active_at TIMESTAMP NOT NULL,
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    is_trial BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS wvs.events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id TEXT NOT NULL REFERENCES wvs.users (user_id),
    internal_user_id BIGINT NOT NULL,
    external_user_id TEXT NOT NULL,
    event_name TEXT NOT NULL,
    channel TEXT NOT NULL,
    event_parameters JSONB,
    inserted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user_id ON wvs.events (user_id);
CREATE INDEX IF NOT EXISTS idx_events_internal_user_id ON wvs.events (internal_user_id);
CREATE INDEX IF NOT EXISTS idx_events_event_name ON wvs.events (event_name);
CREATE INDEX IF NOT EXISTS idx_users_external_user_id ON wvs.users (external_user_id);
