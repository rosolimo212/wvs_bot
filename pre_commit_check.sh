#!/usr/bin/env bash
# Проверки перед коммитом: размер файлов, pytest.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

MAX_BYTES=$((8 * 1024 * 1024))
MAX_LABEL="8 МБ"

human_size() {
    local bytes="$1"
    if command -v numfmt >/dev/null 2>&1; then
        numfmt --to=iec-i --suffix=B --format="%.2f" "$bytes"
        return
    fi
    if [ "$bytes" -ge 1048576 ]; then
        awk "BEGIN {printf \"%.2f МБ\", $bytes / 1048576}"
    elif [ "$bytes" -ge 1024 ]; then
        awk "BEGIN {printf \"%.2f КБ\", $bytes / 1024}"
    else
        printf "%s байт" "$bytes"
    fi
}

collect_checked_files() {
    {
        git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true
        git ls-files 2>/dev/null || true
        git ls-files -o --exclude-standard 2>/dev/null || true
    } | sort -u
}

check_file_sizes() {
    local failed=0
    local file size
    local max_file=""
    local max_size=0
    local large_files=()

    echo "Проверка размеров файлов (лимит: ${MAX_LABEL})..."

    while IFS= read -r file; do
        [ -n "$file" ] || continue
        [ -f "$file" ] || continue

        size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file")

        if [ "$size" -gt "$max_size" ]; then
            max_size="$size"
            max_file="$file"
        fi

        if [ "$size" -gt "$MAX_BYTES" ]; then
            large_files+=("$file|$size")
            failed=1
        fi
    done < <(collect_checked_files)

    if [ -n "$max_file" ]; then
        echo "Самый большой файл: ${max_file} ($(human_size "$max_size"), ${max_size} байт)"
    else
        echo "Самый большой файл: (нет файлов для проверки)"
    fi

    if [ "${#large_files[@]}" -gt 0 ]; then
        echo ""
        echo "ERROR: найдены файлы больше ${MAX_LABEL}:"
        printf '%s\n' "${large_files[@]}" | sort -t'|' -k2 -nr | while IFS='|' read -r path bytes; do
            echo "  - ${path} ($(human_size "$bytes"), ${bytes} байт)"
        done
        echo ""
        exit 1
    fi

    echo "Размеры файлов: OK"
}

check_file_sizes
python3 -m pytest tests/ -q

echo "pre_commit_check: OK"
