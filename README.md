# wvs_bot

World Values Survey bot — короткая анкета (13 вопросов) для оценки индексов ценностей Инглхарта–Вельцеля.

## Архитектура

```
UI (streamlit / telegram / console)
        ↓
   AppService (core/app.py)
        ↓
   brain + logging (postgres / noop)
```

- `main` — prod (VM)
- `dev` — локальная разработка

База: `communication`, схема: `wvs`, таблицы: `wvs.users`, `wvs.events`.

## Быстрый старт

```bash
cd /home/roman/python/wvs_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
# заполните logging.password и при необходимости telegram.token

streamlit run ui/streamlit_app.py
```

При `logging_enabled: true` схема `wvs` и пустые таблицы справочников `tl` создаются автоматически при старте (см. `core/db_schema.py`).

### Справочные данные (аналитика)

Положите в корень проекта `gen_sample.csv` и `country_data.csv`, затем:

```bash
python3 scripts/load_reference_data.py
# только проверить:
python3 scripts/load_reference_data.py --status
```

Таблицы: `tl.gen_sample` (~97k строк), `tl.country_data`. Нужны для пунктов меню «Найти страну» и «Понять своё место в социуме».

## Конфигурация

```yaml
app:
  interface: streamlit   # streamlit | telegram | console
  logging_enabled: true

logging:
  host: localhost
  port: 5432
  database: communication
  user: roman
  password: "..."
  schema: wvs
```

## Тесты

```bash
./pre_commit_check.sh
```

## Legacy MVP

Старые файлы (`streamlit_app.py`, `telegram_back_wvs.py`) сохранены в репозитории для справки.
Новая точка входа — `ui/streamlit_app.py` и `main.py`.
