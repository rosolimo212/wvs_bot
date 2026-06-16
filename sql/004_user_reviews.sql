-- Ответы пользователей на дополнительную анкету.
-- psql -h localhost -U roman -d communication -f sql/004_user_reviews.sql

CREATE TABLE IF NOT EXISTS wvs.user_reviews (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES wvs.users (user_id) ON DELETE CASCADE,
    user_name TEXT NOT NULL,
    qv_id TEXT NOT NULL,
    qv_number INTEGER NOT NULL,
    qv_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    insert_time TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_reviews_user_id ON wvs.user_reviews (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS user_reviews_user_qv_uidx
    ON wvs.user_reviews (user_id, qv_number);
