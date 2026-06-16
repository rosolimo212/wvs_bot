-- Справочные данные WVS для аналитики (сравнение с выборкой, карта стран).
-- Схема tl — как в legacy SQL (find_country.sql, count_pos.sql и др.).
--
-- Загрузка данных из CSV:
--   python3 scripts/load_reference_data.py
--
-- psql -h localhost -U roman -d communication -f sql/005_reference_schema.sql

CREATE SCHEMA IF NOT EXISTS tl;

CREATE TABLE IF NOT EXISTS tl.gen_sample (
    "D_INTERVIEW" BIGINT,
    "B_COUNTRY_ALPHA" TEXT,
    "Q260" INTEGER,
    "Q262" INTEGER,
    "Q173" INTEGER,
    "Q45" INTEGER,
    "Q69" INTEGER,
    "Q6" INTEGER,
    "Q27" INTEGER,
    "Q70" INTEGER,
    "Q65" INTEGER,
    "Q17" INTEGER,
    "Q8" INTEGER,
    "Q11" INTEGER,
    "Q30" INTEGER,
    "Q29" INTEGER,
    "Q33" INTEGER,
    "Q152" INTEGER,
    insert_time TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gen_sample_country ON tl.gen_sample ("B_COUNTRY_ALPHA");
CREATE INDEX IF NOT EXISTS idx_gen_sample_age ON tl.gen_sample ("Q262");

CREATE TABLE IF NOT EXISTS tl.country_data (
    country_code TEXT NOT NULL,
    country_rv DOUBLE PRECISION,
    country_sv DOUBLE PRECISION,
    cluster INTEGER,
    name TEXT,
    "alpha-2" TEXT,
    "alpha-3" TEXT,
    "country-code" INTEGER,
    "iso_3166-2" TEXT,
    region TEXT,
    "sub-region" TEXT,
    "intermediate-region" TEXT,
    "region-code" INTEGER,
    "sub-region-code" INTEGER,
    "intermediate-region-code" DOUBLE PRECISION,
    insert_time TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_country_data_code ON tl.country_data (country_code);
