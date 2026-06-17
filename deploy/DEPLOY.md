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
