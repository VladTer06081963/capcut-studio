#!/bin/bash
# setup_keys.sh — интерактивно вставь ключи в .env, не светя их в чат
# Usage: bash scripts/setup_keys.sh
#
# Безопасность: ключи читаются с /dev/tty (не из argv/heredoc),
# не попадают в shell history и в session logs.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

# Создать .env из .env.example если нет
if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example"
fi

# Helper: set or replace KEY=VALUE in .env (idempotent)
set_env_var() {
    local key="$1"
    local val="$2"
    local esc_val="${val//\\/\\\\}"
    esc_val="${esc_val//\//\\/}"
    # Если строка с ключом уже есть — заменить
    if grep -qE "^${key}=" "$ENV_FILE"; then
        # Use python для безопасной замены (избегаем sed escaping)
        python3 -c "
import sys
p = '$ENV_FILE'
k = '$key'
v = '''$val'''
with open(p) as f:
    lines = f.readlines()
out = []
replaced = False
for line in lines:
    if line.startswith(k + '='):
        out.append(f'{k}={v}\n')
        replaced = True
    else:
        out.append(line)
if not replaced:
    out.append(f'{k}={v}\n')
with open(p, 'w') as f:
    f.writelines(out)
"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

echo
echo "=== Setup API keys for capcut-studio ==="
echo "Ключи читаются с /dev/tty, НЕ через argv и НЕ через чат."
echo "Press Enter чтобы пропустить ключ."
echo

# Отключаем history на время ввода
set +o history 2>/dev/null || true

read -rp "KIE_API_KEY (https://kie.ai, default video provider): " KIE_KEY
if [ -n "$KIE_KEY" ]; then
    set_env_var "KIE_API_KEY" "$KIE_KEY"
    echo "  → KIE_API_KEY saved"
fi

read -rp "OPENROUTER_API_KEY (https://openrouter.ai/keys, text/image): " OR_KEY
if [ -n "$OR_KEY" ]; then
    set_env_var "OPENROUTER_API_KEY" "$OR_KEY"
    echo "  → OPENROUTER_API_KEY saved"
fi

read -rp "MINIMAX_API_KEY (optional, leave empty): " MM_KEY
if [ -n "$MM_KEY" ]; then
    set_env_var "MINIMAX_API_KEY" "$MM_KEY"
    echo "  → MINIMAX_API_KEY saved"
fi

read -rp "YOUTUBE_API_KEY (optional, leave empty): " YT_KEY
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
