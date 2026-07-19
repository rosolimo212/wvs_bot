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

```bash
cd /root/python/wvs_bot && git pull && systemctl restart wvs-streamlit
```

## 7. Daily audience report (Telegram-VM)

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
