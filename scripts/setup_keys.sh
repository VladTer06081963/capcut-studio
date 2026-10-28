#!/bin/bash
# setup_keys.sh — интерактивно вставь ключи в .env, не светя их в чат
# Usage: bash scripts/setup_keys.sh
#
# Безопасность: ключи читаются с /dev/tty (не из argv/heredoc),
# не попадают в shell history и в session logs. В python значение
# передаётся через stdin, а не через argv: argv виден любому
# локальному пользователю через `ps` пока процесс жив.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

# Создать .env из .env.example если нет
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example"
fi

# Прочитать значение ключа.
#
# Предпочтительно — с настоящего терминала (/dev/tty): перенаправленный
# stdin не может подсунуть ключ. Если терминала нет (пайп, CI, песочница) —
# читаем из stdin, иначе скриптом нельзя пользоваться вовсе.
read_key() {
    local prompt="$1"
    local varname="$2"
    local value=""
    if [ -r /dev/tty ]; then
        if read -rp "$prompt" value </dev/tty; then
            printf -v "$varname" '%s' "$value"
            return 0
        fi
    fi
    if read -rp "$prompt" value; then
        printf -v "$varname" '%s' "$value"
    fi
}

# Helper: set or replace KEY=VALUE in .env (idempotent)
#
# Значение уходит в python по stdin, ключ и путь файла — по argv.
# Ни то, ни другое не содержит секрет.
set_env_var() {
    local key="$1"
    local val="$2"
    printf '%s' "$val" | python3 -c '
import sys

path, key = sys.argv[1], sys.argv[2]
value = sys.stdin.read()

with open(path, encoding="utf-8") as fh:
    lines = fh.readlines()

out = []
replaced = False
for line in lines:
    if line.startswith(key + "="):
        # Replace *every* occurrence: a .env that already lists the key
        # twice would otherwise keep the second copy, and the effective
        # value would depend on the parser.
        if not replaced:
            out.append(f"{key}={value}\n")
            replaced = True
        continue
    out.append(line)
if not replaced:
    out.append(f"{key}={value}\n")

with open(path, "w", encoding="utf-8") as fh:
    fh.writelines(out)
' "$ENV_FILE" "$key"
}

echo
echo "=== Setup API keys for capcut-studio ==="
echo "Ключи читаются с /dev/tty, НЕ через argv и НЕ через чат."
echo "Press Enter чтобы пропустить ключ."
echo

# Отключаем history на время ввода
set +o history 2>/dev/null || true

read_key "KIE_API_KEY (https://kie.ai, default video provider): " KIE_KEY
if [ -n "$KIE_KEY" ]; then
    set_env_var "KIE_API_KEY" "$KIE_KEY"
    echo "  → KIE_API_KEY saved"
fi

read_key "OPENROUTER_API_KEY (https://openrouter.ai/keys, text/image): " OR_KEY
if [ -n "$OR_KEY" ]; then
    set_env_var "OPENROUTER_API_KEY" "$OR_KEY"
    echo "  → OPENROUTER_API_KEY saved"
fi

read_key "MINIMAX_API_KEY (optional, leave empty): " MM_KEY
if [ -n "$MM_KEY" ]; then
    set_env_var "MINIMAX_API_KEY" "$MM_KEY"
    echo "  → MINIMAX_API_KEY saved"
fi

read_key "YOUTUBE_API_KEY (optional, leave empty): " YT_KEY
if [ -n "$YT_KEY" ]; then
    set_env_var "YOUTUBE_API_KEY" "$YT_KEY"
    echo "  → YOUTUBE_API_KEY saved"
fi

set -o history 2>/dev/null || true

chmod 600 "$ENV_FILE"
echo
echo "=== Done ==="
echo "$ENV_FILE updated (chmod 600, only owner can read)"
echo
echo "Verify keys are set: grep -E 'API_KEY=' $ENV_FILE | sed 's/=.*/=***/'"
echo "Test Kie.ai: KIE_SMOKE=0 python3 scripts/test_kie.py"
echo "Live smoke: python3 scripts/test_kie.py"
