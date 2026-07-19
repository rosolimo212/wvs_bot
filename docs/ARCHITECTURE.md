# Архитектура wvs_bot

Документ описывает текущее состояние проекта (не план из `task.md`).

## Слои

```
┌─────────────────────────────────────────────────────────────┐
│  ui/          Streamlit · Telegram (aiogram) · Console        │
│               charts, cookies, HTML для Telegram              │
└───────────────────────────┬─────────────────────────────────┘
                            │ handle_action / handle_start
┌───────────────────────────▼─────────────────────────────────┐
│  core/app.py  AppService — оркестратор                        │
│               анкеты, логи, аналитика, FAQ                    │
└───────┬─────────────────────────────┬───────────────────────┘
        │                             │
┌───────▼────────┐           ┌────────▼────────────────────────┐
│  core/brain.py │           │  core/questionnaire/              │
│  чистая логика │           │  core/logging/                    │
│  экранов       │           │  core/analytics/                  │
└────────────────┘           └────────┬──────────────────────────┘
                                      │
                            ┌─────────▼─────────┐
                            │  PostgreSQL       │
                            │  DB communication │
                            │  schema wvs       │
                            └───────────────────┘
```

**Принцип:** интерфейсы не содержат бизнес-логики; `brain` не ходит в БД; аналитика не знает про Telegram/Streamlit.

## Поток данных пользователя

1. **Идентификация** — `channel` + `external_user_id` → стабильный `user_id` (SHA-256), см. `core/identity.py`.
2. **Регистрация** — имя в `users`, событие `registration`.
3. **Анкеты** — ответы в `user_answers` / `user_reviews` (или in-memory при `logging_enabled: false`).
4. **Индексы** — 13 ответов основной анкеты → RV, SV (`core/analytics/indices.py`).
5. **Аналитика** — сравнение с `gen_sample`, `country_data`, другими пользователями бота.
6. **События** — каждый значимый шаг → `events` через `EventLogger`.

## Главное меню (5 пунктов)

| # | Код | Экран |
|---|-----|-------|
| 0 | learn_more | FAQ «Узнать больше» |
| 1 | option_1 | Основная анкета (13 вопросов) |
| 2 | option_2 | Дополнительная (14 вопросов) |
| 3 | option_3 | Найти страну |
| 4 | option_4 | Понять своё место |

Пункты 3–4 заблокированы без основной анкеты; пункт 4 дополнительно требует доп. анкету (страна, год, пол).

## Модули `core/`

| Модуль | Назначение | Вход | Выход |
|--------|------------|------|-------|
| `app.py` | Оркестратор: маршрутизация действий, анкеты, аналитика | `UserIdentity`, action, payload | `AppResponse` |
| `brain.py` | Чистая логика экранов без I/O | тексты, channel | `AppResponse` |
| `models.py` | `Screen`, `AppResponse`, константы действий | — | dataclass / enum |
| `config.py` | Загрузка `config.yaml` | путь к yaml | dict конфигурации |
| `messages.py` | Тексты из `data/dialog_messages.json` | name, channel, placeholders | str |
| `identity.py` | Хеш user_id | channel, external_id | str |
| `error_reporting.py` | Разбор исключений для логов/UI | Exception | dict + traceback |
| `learn_more.py` | FAQ (9 тем) | item id | тексты кнопок/ответов |
| `country_profiles.py` | Карточки стран | country_code | markdown-текст |
| `db.py` | psycopg2 / SQLAlchemy engine | logging_config | connection |
| `db_schema.py` | DDL схемы wvs | — | SQL строки |
| `reference_data.py` | Загрузка CSV в postgres | CSV paths | rows in tables |

### `core/analytics/`

| Модуль | Назначение | Вход | Выход |
|--------|------------|------|-------|
| `indices.py` | RV/SV по 13 ответам | answer_store, user_id | (rv, sv) или None |
| `child_qualities.py` | Парсинг Q11/Q17 (свободный текст) | answer_text | код качества |
| `country.py` | Ближайшая страна | user_id, logging_config | `NearestCountry` |
| `country_lookup.py` | Текст страны → ISO код | текст, catalog | code |
| `position.py` | Место в выборке WVS + сравнение с ботом | RV/SV, profile, SQL | `OwnPlaceResult` |
| `own_place_presentation.py` | Текст и meta графиков option 4 | OwnPlaceResult | (text, meta) |
| `index_interpretation.py` | Пояснения и процентили словами | RV/SV, rank | str |
| `secondary_profile.py` | Парсинг доп. анкеты | answers list | `SecondaryProfile` |
| `sql.py` | Выполнение SQL к reference tables | query, config | rows |

### `core/questionnaire/`

| Модуль | Назначение |
|--------|------------|
| `base.py` | ABC `MainAnswerStore` |
| `postgres.py` | Ответы в `user_answers` / `user_reviews` |
| `memory.py` | In-memory для тестов |
| `factory.py` | Выбор postgres vs memory по `logging_enabled` |
| `loader.py` | `questions.json` → списки вопросов |

### `core/logging/`

| Модуль | Назначение |
|--------|------------|
| `base.py` | ABC `EventLogger` |
| `postgres.py` | users + events в postgres |
| `noop.py` | Заглушка |
| `factory.py` | `build_logger(config)` |

### `core/migration/`

| Модуль | Назначение |
|--------|------------|
| `legacy_import.py` | Импорт CSV из старого бота |

## Модули `ui/`

| Модуль | Назначение |
|--------|------------|
| `streamlit_app.py` | Веб-клиент, Plotly-графики |
| `telegram_bot.py` | aiogram 3, FSM, доставка PNG |
| `console_app.py` | REPL в терминале |
| `base.py` | `build_app_service(config)` |
| `helpers.py` | apply_response, identity в state |
| `interactive_client.py` | Общая логика console + telegram |
| `country_plot.py` | График «найти страну» (matplotlib/plotly) |
| `own_place_plot.py` | Гистограммы option 4 |
| `find_country_delivery.py` | Текст + PNG для Telegram (страна) |
| `own_place_delivery.py` | PNG гистограмм для Telegram |
| `telegram_format.py` | `**bold**` → HTML для Telegram |
| `telegram_session.py` | Bot + proxy для api.telegram.org |
| `streamlit_cookies.py` | Постоянный external_user_id в браузере |
| `streamlit_ui.py` | Контракт UI-тестов Streamlit |

## Модули `scripts/`

| Скрипт | Назначение |
|--------|------------|
| `setup_reference_tables.py` | CSV → `gen_sample`, `country_data` |
| `load_reference_data.py` | Низкоуровневая загрузка CSV |
| `import_legacy_bot.py` | CLI миграции legacy |
| `check_telegram_api.py` | Диагностика Telegram API / proxy |
| `country_plot_timing_check.py` | Замер латентности графика |
| `generate_country_profiles.py` | Генерация `country_profiles.json` |
| `apply_country_data_alter.py` | Миграция колонок country_data |

## Данные (не в git или частично)

| Файл | Содержимое |
|------|------------|
| `questions.json` | main + secondary вопросы |
| `data/dialog_messages.json` | все user-facing строки |
| `data/learn_more_faq.json` | FAQ |
| `data/country_profiles.json` | карточки стран |
| `gen_sample.csv` | выборка WVS (референс) |
| `country_data.csv` | RV/SV по странам |
| `config.yaml` | секреты, interface, logging |

## События (`events.event_name`)

Базовые (из `task.md`): `start_screen_visit`, `registration`, `main_menu_visit`, `main_menu_click`, `main_questionary_start`, `secondary_questionary_start`, `question_show`, `answer_sent`, `find_counry_start`, `find_own_place_start`, `country_plot_loaded`.

Дополнительные: `faq_menu_visit`, `faq_page_visit`, `analytics_error`.

## Деплой

| Компонент | Где крутится |
|-----------|--------------|
| Streamlit | systemd `wvs-streamlit`, порт 8502 |
| Лендинг | nginx → `/var/www/worldvaluessurveybot/index.html` |
| Telegram | отдельный процесс `python main.py` (interface: telegram) |
| Postgres | `communication.wvs` на prod/stage серверах |

Подробнее: [`deploy/DEPLOY.md`](../deploy/DEPLOY.md).

## Тестирование

| Слой | Файл | Что проверяет |
|------|------|---------------|
| 1 | `tests/` + pytest | модули, сценарии, индексы |
| 2 | `business_checks.py` | полный сценарий, события, id, латентность |

Запуск: `./pre_commit_check.sh`.
