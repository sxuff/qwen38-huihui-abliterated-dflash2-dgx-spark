#!/usr/bin/env bash
set -Eeuo pipefail
KEY_FILE="${QWEN38_PROXY_KEY_FILE:-$HOME/.config/qwen38/proxy.key}"
[[ -r "$KEY_FILE" ]] || { echo "proxy key file is unreadable: $KEY_FILE" >&2; exit 2; }
export QWEN38_PROXY_KEY_FILE="$KEY_FILE"
export QWEN38_PROXY_HOST="${QWEN38_PROXY_HOST:-172.17.0.1}"
export QWEN38_PROXY_PORT="${QWEN38_PROXY_PORT:-8001}"
export QWEN38_UPSTREAM_HOST="${QWEN38_UPSTREAM_HOST:-127.0.0.1}"
export QWEN38_UPSTREAM_PORT="${QWEN38_UPSTREAM_PORT:-8002}"
exec /usr/bin/python3 "$HOME/.local/bin/qwen38-auth-proxy.py"

