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
cd /root/python/wvs_bot
./scripts/deploy_prod.sh
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

### Telegram на проде

Отдельного unit в репозитории нет. Если бот запущен вручную:

```bash
ps aux | grep -E 'telegram_bot|main.py' | grep -v grep
pkill -f 'main.py' || pkill -f 'telegram_bot' || true

cd /root/python/wvs_bot
source .venv/bin/activate
nohup python main.py >> /var/log/wvs-telegram.log 2>&1 &
```

(или оформите свой `wvs-telegram.service` по аналогии с `deploy/wvs-streamlit.service`, с `ExecStart=... python main.py` и `interface: telegram` в `config.yaml`.)
