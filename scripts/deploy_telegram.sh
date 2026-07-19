#!/usr/bin/env bash
# Обновление на TELEGRAM-VM: код, зависимости, бот, unit’ы daily-report.
#
# Требования в config.yaml:
#   app.interface: telegram
#   logging.host → Postgres основной VM
#   communication.daily_audience_report.chat_id / send_at
#
# SQL-миграции здесь НЕ накатывать (БД на основной VM).
set -euo pipefail

ROOT="${WVS_ROOT:-/root/python/wvs_bot}"
BRANCH="${WVS_DEPLOY_BRANCH:-main}"

cd "$ROOT"

echo "==> git fetch / checkout ${BRANCH} / pull"
git fetch origin
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

# shellcheck disable=SC1091
source .venv/bin/activate
echo "==> pip install"
pip install -q -r requirements.txt

echo "==> install/refresh systemd units"
cp deploy/wvs-telegram.service /etc/systemd/system/
cp deploy/wvs-daily-audience-report.service /etc/systemd/system/
cp deploy/wvs-daily-audience-report.timer /etc/systemd/system/
systemctl daemon-reload

# Если раньше крутился nohup — один раз убейте старый процесс, иначе будет конфликт polling.
if ! systemctl is-enabled wvs-telegram >/dev/null 2>&1; then
  echo "==> enable wvs-telegram (первый запуск)"
  systemctl enable wvs-telegram
fi
if ! systemctl is-enabled wvs-daily-audience-report.timer >/dev/null 2>&1; then
  echo "==> enable daily-audience timer (первый запуск)"
  systemctl enable wvs-daily-audience-report.timer
fi

echo "==> restart telegram bot + ensure timer active"
systemctl restart wvs-telegram
systemctl start wvs-daily-audience-report.timer
systemctl --no-pager --full status wvs-telegram || true
systemctl --no-pager list-timers 'wvs-daily*' || true

echo "OK: Telegram-VM updated (branch=${BRANCH})."
echo "    Логи бота: journalctl -u wvs-telegram -f"
echo "    Daily report: journalctl -u wvs-daily-audience-report.service -n 30"
