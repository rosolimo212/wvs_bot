# Backlog — запланировано, но ещё не сделано

Сводка по `task.md` и коду на момент завершения MVP. В коде **нет** маркеров `TODO`/`FIXME` — открытые пункты собраны здесь.

## Архитектура (из task.md)

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| Одновременный запуск streamlit + telegram + console | ❌ | Один `app.interface` в `config.yaml`, один процесс `main.py` |
| Альтернативные логгеры (SQLite, ClickHouse) | ❌ | Только `PostgresLogger` + `NoopLogger` |
| Ввод изображения / геопозиции | ❌ | Только `choice` и `text` в анкете |
| Отдельный модуль «коллектор информации» | ⚠️ | Логика размазана: `questionnaire/`, `reference_data.py`, scripts |
| Опция «выключить бота» отдельно от логирования | ⚠️ | `logging_enabled: false` отключает и БД, и персистентность ответов |

## Продукт

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| Главное меню ровно 4 пункта | ⚠️ | Добавлен 5-й: «Узнать больше» (FAQ) — осознанное расширение |
| `is_paid` / `is_trial` в users | ❌ | Колонки есть, приложение не выставляет |
| Латентность Telegram &lt; 8 с (реальный клиент) | ❌ | `business_checks.py` — in-memory сценарий, не prod Telegram |
| Латентность Streamlit &lt; 8 с (реальный UI) | ❌ | То же |
| `country_plot_loaded` в REQUIRED_EVENTS | ⚠️ | Логируется, но не в списке обязательных событий business_checks |

## Инфраструктура

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| systemd unit для Telegram | ❌ | Только `wvs-streamlit.service` в репо |
| Автокопирование лендинга при deploy | ❌ | Ручной `cp deploy/www/index.html` |
| CI/CD (GitHub Actions) | ❌ | Деплой вручную на VM |

## Документация

| Пункт | Статус |
|-------|--------|
| README отражает Telegram-графики | ✅ (обновлено) |
| task.md отражает 5 пунктов меню и FAQ | ⚠️ (частично в README / ARCHITECTURE) |
| PEP8 docstrings на всех модулях | ⚠️ (в процессе, см. docstrings в коде) |

## Рекомендуемый порядок следующих шагов

1. **systemd для Telegram** — `deploy/wvs-telegram.service`, как streamlit.
2. **Deploy script** — `scripts/deploy_prod.sh`: pull, pip, cp landing, restart units.
3. **Пер-client latency smoke** — curl/streamlit health + telegram webhook ping в business_checks или отдельный cron.
4. **SQLite logger** — если нужен локальный офлайн-режим без postgres (из task.md).
5. **Мониторинг** — алерт на `analytics_error` в events, дашборд по DAU/воронке анкеты.
