# Backlog — запланировано, но ещё не сделано

Сводка по `task.md` и коду. Практический приоритетный список — [`TODO.md`](TODO.md).

## Архитектура (из task.md)

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| Одновременный запуск streamlit + telegram + console | ❌ | Один `app.interface` в `config.yaml`, один процесс `main.py` |
| Альтернативные логгеры (SQLite, ClickHouse) | ❌ | Только `PostgresLogger` + `NoopLogger` |
| Ввод изображения / геопозиции | ❌ | Только `choice` и `text` в анкете |
| Отдельный модуль «коллектор информации» | ⚠️ | Логика в `questionnaire/`, `reference_data.py`, scripts |
| Опция «выключить бота» отдельно от логирования | ⚠️ | `logging_enabled: false` отключает и БД, и персистентность ответов |
| Исходящие коммуникации / дайджесты | ✅ | `core/communication/`, CLI, timer |

## Продукт

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| Главное меню ровно 4 пункта | ⚠️ | 5-й: «Узнать больше» (FAQ) — осознанное расширение |
| `is_paid` / `is_trial` в users | ❌ | Колонки есть, приложение не выставляет |
| Deep link `?start=faq` → экран FAQ | ❌ | Шаблон `faq_deeplink` есть; маршрутизация payload — нет |
| Inline-кнопки в рассылках | ❌ | Пока только текст (+ URL) |
| Латентность Telegram/Streamlit &lt; 8 с (реальный клиент) | ❌ | `business_checks` — in-memory |
| `country_plot_loaded` в REQUIRED_EVENTS | ⚠️ | Логируется, не в обязательном списке business_checks |

## Инфраструктура

| Пункт | Статус | Комментарий |
|-------|--------|-------------|
| systemd unit для Telegram | ✅ | `deploy/wvs-telegram.service`, `scripts/deploy_telegram.sh` |
| Deploy script | ✅ | `deploy_prod.sh` (основная VM), `deploy_telegram.sh` (Telegram-VM) |
| CI/CD (GitHub Actions) | ❌ | Деплой вручную на VM |
| Мониторинг DAU / ошибок рассылок | ❌ | См. TODO §B |

## Документация

| Пункт | Статус |
|-------|--------|
| README / ARCHITECTURE / AGENTS | ✅ обновлено под communication + split deploy |
| task.md отражает 5 пунктов меню и FAQ | ⚠️ частично |
| PEP8 docstrings на всех модулях | ⚠️ по мере правок |

## Рекомендуемый порядок

См. [`TODO.md`](TODO.md) — блоки **A (сейчас)** и **B (нагрузка)**.
