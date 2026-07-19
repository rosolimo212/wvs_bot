-- Журнал исходящих коммуникаций (рассылки в Telegram).
-- Имя таблицы: wvs.communications (множественное число).
-- Не путать с именем базы данных communication.
--
-- Ручная установка (на хосте Postgres / основной VM):
--   psql -h localhost -U roman -d communication -f sql/006_communications.sql

CREATE SEQUENCE IF NOT EXISTS wvs.communications_communication_id_seq;

CREATE TABLE IF NOT EXISTS wvs.communications (
    communication_id BIGINT PRIMARY KEY,
    user_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    sending_time TIMESTAMP NOT NULL,
    status TEXT NOT NULL
);

ALTER SEQUENCE wvs.communications_communication_id_seq
    OWNED BY wvs.communications.communication_id;

CREATE UNIQUE INDEX IF NOT EXISTS communications_user_template_uidx
    ON wvs.communications (user_id, template_id);

CREATE INDEX IF NOT EXISTS idx_communications_user_id
    ON wvs.communications (user_id);

CREATE INDEX IF NOT EXISTS idx_communications_template_id
    ON wvs.communications (template_id);

CREATE INDEX IF NOT EXISTS idx_communications_sending_time
    ON wvs.communications (sending_time);
