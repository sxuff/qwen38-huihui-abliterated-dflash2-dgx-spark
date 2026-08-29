#!/usr/bin/env bash
set -Eeuo pipefail
NAME="${NAME:-qwen38-huihui-radixark-nvfp4-manual}"
OWNER="${OWNER:-manual}"
if ! docker inspect "$NAME" >/dev/null 2>&1; then exit 0; fi
recipe=$(docker inspect -f '{{index .Config.Labels "io.sxuff.qwen38.recipe"}}' "$NAME" 2>/dev/null || true)
existing_owner=$(docker inspect -f '{{index .Config.Labels "io.sxuff.qwen38.owner"}}' "$NAME" 2>/dev/null || true)
[[ "$recipe" == true && "$existing_owner" == "$OWNER" ]] || {
  echo "refusing to stop container $NAME: expected owner=$OWNER actual=${existing_owner:-unset}" >&2
  exit 2
}
docker rm -f "$NAME" >/dev/null
