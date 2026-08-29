#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${QWEN38_PROXY_KEY_FILE:-$HOME/.config/qwen38/proxy.key}"
[[ -s "$KEY_FILE" ]] || { echo "missing proxy key: $KEY_FILE" >&2; exit 2; }
mode=$(stat -c %a "$KEY_FILE")
[[ "$mode" == 600 || "$mode" == 400 ]] || { echo "proxy key mode must be 600 or 400, got $mode" >&2; exit 2; }
install -Dm0755 "$ROOT/deploy/qwen38-huihui-radixark-dflash2-service.sh" "$HOME/.local/bin/qwen38-huihui-radixark-dflash2-service.sh"
install -Dm0755 "$ROOT/deploy/qwen38-auth-proxy-service.sh" "$HOME/.local/bin/qwen38-auth-proxy-service.sh"
install -Dm0755 "$ROOT/deploy/qwen38-auth-proxy.py" "$HOME/.local/bin/qwen38-auth-proxy.py"
install -Dm0644 "$ROOT/deploy/qwen38-huihui-radixark-dflash2.service" "$HOME/.config/systemd/user/qwen38-huihui-radixark-dflash2.service"
install -Dm0644 "$ROOT/deploy/qwen38-huihui-radixark-dflash2-proxy.service" "$HOME/.config/systemd/user/qwen38-huihui-radixark-dflash2-proxy.service"
systemctl --user daemon-reload
printf '%s
' 'Installed without starting.' 'Start explicitly with:' 'systemctl --user enable --now qwen38-huihui-radixark-dflash2.service qwen38-huihui-radixark-dflash2-proxy.service'
