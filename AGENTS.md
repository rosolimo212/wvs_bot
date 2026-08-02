# AGENTS.md — контекст для AI-агентов и разработчиков

Краткая выжимка по проекту **wvs_bot**. Читать перед правками кода. Детали: `docs/ARCHITECTURE.md`, `task.md`, `deploy/DEPLOY.md`, `docs/TODO.md`.

## Что это

Интерактивный опрос в духе World Values Survey: основная анкета (13 Q) → индексы **RV/SV**, «найти страну», «своё место»; доп. анкета (14 Q); FAQ.  
Интерфейсы: **Streamlit**, **Telegram** (aiogram), **console** — один `app.interface` на процесс.

## Нелокальные инварианты

1. **UI не содержит бизнес-логики** — только `AppService.handle_start` / `handle_action` и отрисовка `AppResponse`.
2. **`brain.py` без I/O** — только тексты/кнопки/экраны.
3. **Тексты пользователю** — `data/dialog_messages.json` (+ FAQ/profiles JSON), не хардкод в UI.
4. **`user_id`** = sha256(`channel:external_user_id`), см. `core/identity.py`.
5. **Каналы в БД:** `streamlit` | `telegram` | `console`. В UI/сообщениях streamlit часто зовётся «браузер».
6. **Схема логов:** БД `communication`, схема **`wvs`** (обязательно в config).
7. **Ветки:** `main` → prod, `dev` → разработка. Секреты только в `config.yaml` (gitignore).
8. **Не вызывать `move_agent_to_root` / смену workspace**, если пользователь просит работать в текущем дереве `/…/wvs_bot` — это долго.

## Прод-топология (важно!)

| Роль | Где |
|------|-----|
| Postgres | Основная VM (Россия), БД `communication` |
| Streamlit + лендинг | Основная VM |
| Telegram-бот + исходящие коммуникации | **Отдельная Telegram-VM** (доступ к `api.telegram.org`, часто нужен `telegram.proxy_url` на RU VPS) |

Бот на Telegram-VM пишет в Postgres **по сети** (`logging.host` = IP основной).  
Миграции SQL (`sql/*.sql`) накатывать **на Postgres основной VM**, не на сокет Telegram-VM.

Деплой:
- основная VM → `scripts/deploy_prod.sh` (Streamlit + лендинг);
- Telegram-VM → `scripts/deploy_telegram.sh` (unit `wvs-telegram` + daily-report timer).
При редких релизах достаточно ручного pull на затронутой машине.

## Индексы RV/SV

- Считаются в Python (`core/analytics/indices.py`, `wvs_index_sums.py`).
- Ответы «Не знаю» / коды ≤0 **не входят** в сумму.
- Предупреждение пользователю при **≥5** «не знаю» (`UNKNOWN_ANSWER_WARN_THRESHOLD`).
- «Заполнена основная» для сегментов/метрик: есть ответ с **`qv_number = 13`** в `user_answers`.
- «Заполнена доп.»: **`qv_number = 14`** в `user_reviews`.

## Telegram: имена и регистрация

- Новый пользователь с `@username` → экран подтверждения имени; событие **`registration` только после confirm**, не на `/start`.
- В старых записях в `user_name` мог лежать numeric `external_user_id` — чинит `resolve_telegram_user_name`.
- Приветствие: `greeting_display_name` добавляет `@` для telegram username.
- Тексты в Telegram: `**bold**` → HTML (`ui/telegram_format.py`, `parse_mode=HTML`).
- Deep link: `https://t.me/values_counter_bot?start=<payload>` (шаблон `faq_deeplink` в JSON). Payload `faq` **пока не маршрутизируется** в FAQ — только обычный `/start`/меню.

## Исходящая коммуникация (`core/communication/`)

| Часть | Назначение |
|-------|------------|
| Daily report | Метрики аудитории → stats-чат; `send_at` в config; systemd timer **каждую минуту**, gate по времени |
| Campaigns | Ручные рассылки только `registration_channel=telegram` |
| Таблица | **`wvs.communications`** (мн. число!), не `communication` |
| Шаблоны | `data/communication_messages.json`, плейсхолдер `{user_name}` |
| Сегменты | `test` (stats `chat_id`), `all_users`, `primary_complete`, `both_complete` |
| Идемпотентность | UNIQUE `(user_id, template_id)`; INSERT на каждую **попытку** send (`status` sent/failed:…) |
| Rate limit | ≤1 коммуникация / час на `user_id` (skip **без** INSERT); пауза 1–3 с между sends в прогоне |
| CLI | `scripts/send_daily_audience_report.py`, `scripts/send_communication.py` |

Тест рассылки: `--segment test` → тот же `chat_id`, что daily report; `user_id=system:stats_chat`.

## Аналитика: частые ловушки API

- `find_nearest_country(answer_store, user_id, logging_config, reference_schema=…)`.
- В notebook/`tests.ipynb` не вызывать старую сигнатуру без `answer_store`.
- Legacy import: `events` без `user_name` не должны перетирать ник numeric id (`_pick_user_name` в `legacy_import.py`).
- Опечатка в событии сохранена: **`find_counry_start`**.

## SQL-миграции

По порядку в `sql/`: `001_init` … `005_reference`, плюс `006_communications.sql` (рассылки).  
Есть также `006_alter_country_data.sql` — другое назначение; не путать с communications.

## Тесты

```bash
pytest tests/                 # слой 1
python3 business_checks.py    # слой 2
./pre_commit_check.sh
```

Коммиты — только по явной просьбе пользователя. Push — только по просьбе.

## Куда смотреть дальше

- Открытые задачи: [`docs/TODO.md`](docs/TODO.md)
- Backlog / task gaps: [`docs/BACKLOG.md`](docs/BACKLOG.md)
- Деплой: [`deploy/DEPLOY.md`](deploy/DEPLOY.md)
- **Отложено — PNG для соцсетей:** [`docs/SHARE_IMAGE_DEFERRED.md`](docs/SHARE_IMAGE_DEFERRED.md) (полный контекст: цель, итерации, почему не в main, как чинить UX Streamlit)
