#!/usr/bin/env bash
# Обновление prod на VM (streamlit + лендинг). Telegram — отдельно, см. docs/BACKLOG.md.
set -euo pipefail

ROOT="${WVS_ROOT:-/root/python/wvs_bot}"
LANDING_DIR="${WVS_LANDING_DIR:-/var/www/worldvaluessurveybot}"

cd "$ROOT"
git pull
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

cp deploy/www/index.html "$LANDING_DIR/"

systemctl restart wvs-streamlit
systemctl status wvs-streamlit --no-pager

echo "OK: streamlit restarted, landing copied."
