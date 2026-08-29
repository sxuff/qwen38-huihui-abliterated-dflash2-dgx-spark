#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${QWEN38_RECIPE_ROOT:-$HOME/qwen38-27b-huihui-radixark-abliterated-nvfp4-dflash2-dgx-spark}"
MODEL_DIR="${QWEN38_MODEL_DIR:-$HOME/models/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4-21565d389fe5/snapshot}"
DRAFT_DIR="${QWEN38_DRAFT_DIR:-$HOME/.cache/qwen38-spec-drafts/hub/models--z-lab--Qwen3.8-27B-DFlash2/snapshots/50307d4c4cde6860d4eee73e2547cd786fe8e8a4}"
export MODEL_DIR DRAFT_DIR
export IMAGE="sxuff/qwen38-27b-abliterated-dflash2:2026-08-29"
export NAME="qwen38-huihui-radixark-nvfp4"
export OWNER="systemd:qwen38-huihui-radixark-dflash2"
export HOST=127.0.0.1 PORT=8002
export STATE_DIR="$HOME/.local/state/qwen38-huihui-radixark-dflash2"
exec "$ROOT/scripts/serve.sh"
