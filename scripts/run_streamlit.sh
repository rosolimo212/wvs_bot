#!/usr/bin/env bash
# Запуск Streamlit для продакшена (0.0.0.0:8502, см. .streamlit/config.toml).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

exec streamlit run ui/streamlit_app.py "$@"
