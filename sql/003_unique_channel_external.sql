-- Уникальность: один external_user_id на канал = одна строка users.
-- psql -h localhost -U roman -d communication -f sql/003_unique_channel_external.sql

CREATE UNIQUE INDEX IF NOT EXISTS users_channel_external_uidx
    ON wvs.users (registration_channel, external_user_id);
