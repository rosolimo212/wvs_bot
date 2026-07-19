# Деплой Streamlit на VM

Субдомен: **https://streamlit.worldvaluessurveybot.info**  
Сервер: `45.132.18.2`, приложение слушает `127.0.0.1:8502` (порт 8501 занят template-streamlit).

## 1. DNS (reg.ru)

В зоне `worldvaluessurveybot.info`:

| Тип | Имя (хост) | Значение |
|-----|------------|----------|
| A   | `streamlit` | `45.132.18.2` |

Проверка:

```bash
dig +short streamlit.worldvaluessurveybot.info
```

## 2. Код и зависимости на VM

```bash
cd /root/python/wvs_bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # если ещё нет; заполнить secrets
python scripts/setup_reference_tables.py   # один раз
```

## 3. Streamlit (только localhost за nginx)

В `.streamlit/config.toml` на проде:

```toml
[server]
address = "127.0.0.1"
port = 8502
headless = true
enableCORS = false

[browser]
serverAddress = "streamlit.worldvaluessurveybot.info"
gatherUsageStats = false
```

Локальная разработка: `address = "0.0.0.0"` (как в репозитории по умолчанию).

## 4. systemd

```bash
cp deploy/wvs-streamlit.service /etc/systemd/system/
chmod +x scripts/run_streamlit.sh
systemctl daemon-reload
systemctl enable wvs-streamlit
systemctl start wvs-streamlit
systemctl status wvs-streamlit
```

Логи: `journalctl -u wvs-streamlit -f`

## 5. Nginx + HTTPS

```bash
apt install -y nginx certbot python3-certbot-nginx
ufw allow 80/tcp
ufw allow 443/tcp

cp deploy/nginx-streamlit.conf /etc/nginx/sites-available/wvs-streamlit
ln -sf /etc/nginx/sites-available/wvs-streamlit /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

certbot --nginx -d streamlit.worldvaluessurveybot.info
```

Порт **8502** наружу открывать не нужно — только 80/443.

## 6. Обновление

**Основная VM** (Streamlit + лендинг):

```bash
cd /root/python/wvs_bot
./scripts/deploy_prod.sh
```

**Telegram-VM** (бот + daily-report units):

```bash
cd /root/python/wvs_bot
./scripts/deploy_telegram.sh
```

Или вручную:

**Лендинг** (`worldvaluessurveybot.info`) — отдельная копия HTML; после pull: `cp deploy/www/index.html /var/www/worldvaluessurveybot/`.

**Индексы стран** после обновления методологии или gen_sample:

```bash
python3 scripts/recompute_reference_indices.py
```

Полная перезагрузка справочников (CSV + пересчёт country_rv/sv):

```bash
python3 scripts/setup_reference_tables.py
```

Проверка:

```bash
grep -o '<title>[^<]*' /var/www/worldvaluessurveybot/index.html
```

Если Telegram запущен отдельным процессом — перезапустите и его (см. ниже).

## 7. Если `Unit wvs-streamlit.service not found`

`git pull` **не создаёт** systemd-unit. Скорее всего Streamlit на проде когда-то запускали вручную (`nohup`, `screen`, другой unit), поэтому после pull крутится **старый процесс**, а `systemctl restart wvs-streamlit` не находит сервис.

**Пароль при systemctl** — вы залогинены не под `root` (например, под `roman`). Либо `sudo systemctl …`, либо `su -` / вход под root. Раньше, если работали сразу под root, пароль не спрашивали.

### Диагностика (на VM)

```bash
whoami
ps aux | grep -E 'streamlit|wvs_bot' | grep -v grep
ss -tlnp | grep 8502
systemctl list-unit-files | grep -i streamlit
ls -la /etc/systemd/system/wvs-streamlit.service
```

### Однократная установка unit (под root)

```bash
cd /root/python/wvs_bot
source .venv/bin/activate
pip install -r requirements.txt

cp deploy/wvs-streamlit.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable wvs-streamlit
```

Если порт 8502 уже занят старым процессом — остановите его (`kill <PID>` из `ps aux`) или:

```bash
systemctl stop wvs-streamlit 2>/dev/null || true
# убить зависший ручной streamlit, если есть
pkill -f 'streamlit run ui/streamlit_app.py' || true

systemctl start wvs-streamlit
systemctl status wvs-streamlit
journalctl -u wvs-streamlit -n 30 --no-pager
```

Проверка снаружи: https://streamlit.worldvaluessurveybot.info

### Telegram на проде (Telegram-VM)

Unit в репозитории: `deploy/wvs-telegram.service`.  
В `config.yaml` на этой VM: `app.interface: telegram`, `logging.host` → Postgres основной машины.

**Первая установка (под root):**

```bash
cd /root/python/wvs_bot
# остановить старый nohup/polling, иначе конфликт getUpdates:
pkill -f '/root/python/wvs_bot/main.py' 2>/dev/null || true
pkill -f 'python main.py' 2>/dev/null || true

cp deploy/wvs-telegram.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wvs-telegram
systemctl status wvs-telegram
journalctl -u wvs-telegram -n 30 --no-pager
```

**Обычное обновление:**

```bash
./scripts/deploy_telegram.sh
```

Логи: `journalctl -u wvs-telegram -f`

## 8. Daily audience report (Telegram-VM)

Ежедневный дайджест в служебный чат. Время задаётся в **config.yaml** (`send_at`),
systemd timer каждую минуту запускает скрипт; отправка только в нужную минуту.

1. В `config.yaml` на Telegram-VM:

```yaml
communication:
  daily_audience_report:
    enabled: true
    chat_id: "-100xxxxxxxxxx"
    timezone: Europe/Moscow
    send_at: "11:04"
```

2. Проверка без отправки / принудительная отправка:

```bash
cd /root/python/wvs_bot
.venv/bin/python scripts/send_daily_audience_report.py --dry-run
.venv/bin/python scripts/send_daily_audience_report.py --force
```

Тест по расписанию: поставьте `send_at` на ближайшую минуту и подождите timer
(перезапускать systemd не нужно — конфиг читается при каждом запуске).

3. Установка timer:

```bash
cp deploy/wvs-daily-audience-report.service /etc/systemd/system/
cp deploy/wvs-daily-audience-report.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wvs-daily-audience-report.timer
systemctl list-timers | grep wvs-daily
```

Разовый прогон: `systemctl start wvs-daily-audience-report.service`  
Логи: `journalctl -u wvs-daily-audience-report.service -n 50`

## 9. Исходящие коммуникации (рассылки)

Таблица журнала (один раз на DB):

```bash
psql -h <host> -U <user> -d communication -f sql/006_communications.sql
```

Шаблоны: `data/communication_messages.json`.  
Ручной запуск (Telegram-VM):

```bash
# тест в stats-чат
.venv/bin/python scripts/send_communication.py --template stub_empty --segment test --dry-run
.venv/bin/python scripts/send_communication.py --template stub_empty --segment test

# сегменты: test | all_users | primary_complete | both_complete
```

Идемпотентность: одна пара `(user_id, template_id)`.  
Rate limit: не чаще одной коммуникации в час на `user_id` (пропуск без INSERT).  
Пауза между сообщениями в прогоне: `--pause-sec` (по умолчанию 2).
