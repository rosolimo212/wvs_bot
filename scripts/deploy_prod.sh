#!/usr/bin/env bash
# Обновление prod на ОСНОВНОЙ VM: код, зависимости, лендинг, Streamlit.
#
# Не трогает: Telegram-бот, daily-report timer (они на Telegram-VM —
# см. scripts/deploy_telegram.sh).
#
# SQL-миграции (sql/*.sql) накатывайте отдельно на Postgres этой машины.
set -euo pipefail

ROOT="${WVS_ROOT:-/root/python/wvs_bot}"
LANDING_DIR="${WVS_LANDING_DIR:-/var/www/worldvaluessurveybot}"
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

if [[ -d "${LANDING_DIR}" ]]; then
  echo "==> landing → ${LANDING_DIR}"
  cp deploy/www/index.html "${LANDING_DIR}/"
else
  echo "WARN: ${LANDING_DIR} нет — лендинг не скопирован (создайте каталог или задайте WVS_LANDING_DIR)"
fi

echo "==> restart wvs-streamlit"
systemctl restart wvs-streamlit
systemctl --no-pager --full status wvs-streamlit || true

echo "OK: main VM updated (branch=${BRANCH})."
echo "    Telegram-VM: scripts/deploy_telegram.sh"
echo "    Новые sql/*.sql — накатить вручную на Postgres этой VM."
