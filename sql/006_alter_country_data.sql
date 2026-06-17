-- Дополнительные поля справочника стран.
-- По умолчанию схема tl (analytics.reference_schema в config.yaml).
--
-- Применение:
--   psql -h localhost -U roman -d communication -v schema=tl -f sql/006_alter_country_data.sql
-- или:
--   python3 scripts/apply_country_data_alter.py

ALTER TABLE :schema.country_data
    ADD COLUMN IF NOT EXISTS full_name TEXT,
    ADD COLUMN IF NOT EXISTS government_type TEXT,
    ADD COLUMN IF NOT EXISTS gdp_per_capita_usd BIGINT,
    ADD COLUMN IF NOT EXISTS population BIGINT,
    ADD COLUMN IF NOT EXISTS flight_hours_from_london NUMERIC(5, 1);
