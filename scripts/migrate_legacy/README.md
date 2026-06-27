# Импорт legacy Telegram-бота

Данные прошлой итерации лежали в схеме `tl` с **числовым Telegram ID** в колонке `user_id`.
Новый бот использует `wvs.*` и хеш `sha256("telegram:" + telegram_id)`.

## Файлы

| Файл | Legacy-таблица | Назначение |
|------|----------------|------------|
| `main_answers.csv` | `tl.user_answers` | 13 вопросов основной анкеты |
| `reviews.csv` | `tl.user_reviews` | дополнительная анкета (S01–S13) |
| `events.csv` | `tl.wvs_events` | история действий |

## Колонки CSV

### main_answers.csv / reviews.csv

| Колонка | Обязательно | Описание |
|---------|-------------|----------|
| `user_id` | да | Telegram ID (например `123456789`) |
| `user_name` | да | username или имя в боте |
| `qv_id` | да | `Q173`, `S02`, … |
| `qv_number` | да | порядковый номер вопроса |
| `qv_text` | да | текст вопроса |
| `answer_text` | да | ответ пользователя |
| `insert_time` | нет | `2024-06-01 12:00:00` |

### events.csv

| Колонка | Обязательно | Описание |
|---------|-------------|----------|
| `user_id` | да | Telegram ID |
| `event_type` | да | legacy-имя события |
| `parameters` | нет | JSON (объект или список с одним объектом) |
| `timestamp` | нет | время события |

Пример строки events:

```csv
123456789,record_answer,"[{""qv_number"": 3}]",2024-06-01 12:05:00
```

## Маппинг событий

| Legacy `event_type` | Новый `event_name` |
|---------------------|-------------------|
| `main_menu` | `main_menu_visit` |
| `main_questionary` | `main_questionary_start` |
| `secondary_questionary` | `secondary_questionary_start` |
| `record_answer` | `answer_sent` |
| `find_country` | `find_counry_start` |
| `find_position` | `find_own_place_start` |
| `questions_finished` | *(пропуск)* |
| `secondary_questions_finished` | *(пропуск)* |

## Запуск

```bash
cd /home/roman/python/wvs_bot

# Проверка без записи
python3 scripts/import_legacy_bot.py \
  --main-answers scripts/migrate_legacy/main_answers.csv \
  --reviews scripts/migrate_legacy/reviews.csv \
  --events scripts/migrate_legacy/events.csv \
  --dry-run

# Импорт в prod (config.yaml → logging.schema = wvs)
python3 scripts/import_legacy_bot.py \
  --main-answers scripts/migrate_legacy/main_answers.csv \
  --reviews scripts/migrate_legacy/reviews.csv \
  --events scripts/migrate_legacy/events.csv
```

## Поведение при повторах

- Пользователь с тем же `(telegram, external_user_id)` не создаётся повторно.
- Ответы: `ON CONFLICT (user_id, qv_number) DO UPDATE`.
- События всегда добавляются новыми строками (дубликаты не дедуплицируются).

## Экспорт из legacy Postgres

```sql
\copy (
  SELECT user_id, user_name, qv_id, qv_number, qv_text, answer_text, insert_time
  FROM tl.user_answers ORDER BY user_id, qv_number
) TO 'main_answers.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy (
  SELECT user_id, user_name, qv_id, qv_number, qv_text, answer_text, insert_time
  FROM tl.user_reviews ORDER BY user_id, qv_number
) TO 'reviews.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy (
  SELECT user_id, event_type, parameters, insert_time AS timestamp
  FROM tl.wvs_events ORDER BY insert_time
) TO 'events.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
```

Если в legacy колонка времени называлась иначе — переименуйте в `timestamp` или `insert_time` в CSV.
