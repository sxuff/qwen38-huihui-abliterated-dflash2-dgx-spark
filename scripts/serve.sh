#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:?set MODEL_DIR to the pinned candidate snapshot}"
DRAFT_DIR="${DRAFT_DIR:?set DRAFT_DIR to the pinned DFlash2 draft snapshot}"
IMAGE="${IMAGE:-sxuff/qwen38-27b-abliterated-dflash2:2026-08-29}"
NAME="${NAME:-qwen38-huihui-radixark-nvfp4-manual}"
OWNER="${OWNER:-manual}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8001}"
MEM_FRACTION_STATIC="${MEM_FRACTION_STATIC:-0.70}"
CPUSET="${CPUSET:-5-9,15-19}"
STATE_DIR="${STATE_DIR:-$ROOT/.state}"
MODE=dflash2
mkdir -p "$STATE_DIR"
python3 "$ROOT/scripts/verify_contract.py" >/dev/null
python3 "$ROOT/scripts/verify_artifacts.py" --manifest "$ROOT/manifests/target.json" --root "$MODEL_DIR" --report "$STATE_DIR/target-verification.json" >/dev/null
python3 "$ROOT/scripts/verify_artifacts.py" --manifest "$ROOT/manifests/draft.json" --root "$DRAFT_DIR" --report "$STATE_DIR/draft-verification.json" >/dev/null
EXPECTED_IMAGE_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' "$ROOT/runtime-manifest.json")"
ACTUAL_IMAGE_ID="$(docker image inspect "$IMAGE" --format '{{.Id}}')"
[[ "$ACTUAL_IMAGE_ID" == "$EXPECTED_IMAGE_ID" ]] || { echo "image identity mismatch: expected=$EXPECTED_IMAGE_ID actual=$ACTUAL_IMAGE_ID" >&2; exit 2; }
docker image inspect "$IMAGE" --format '{{json .Config.Labels}}' > "$STATE_DIR/image-labels.json"
if docker inspect "$NAME" >/dev/null 2>&1; then
  recipe=$(docker inspect -f '{{index .Config.Labels "io.sxuff.qwen38.recipe"}}' "$NAME" 2>/dev/null || true)
  existing_owner=$(docker inspect -f '{{index .Config.Labels "io.sxuff.qwen38.owner"}}' "$NAME" 2>/dev/null || true)
  [[ "$recipe" == true && "$existing_owner" == "$OWNER" ]] || {
    echo "refusing to touch container $NAME: expected owner=$OWNER actual=${existing_owner:-unset}" >&2
    exit 2
  }
  docker rm -f "$NAME" >/dev/null
fi
args=(python3 -m sglang.launch_server --trust-remote-code --model-path /model --served-model-name qwen38-27b-huihui-radixark-abliterated-nvfp4 --mem-fraction-static "$MEM_FRACTION_STATIC" --attention-backend flashinfer --chunked-prefill-size 8192 --disable-prefill-cuda-graph --kv-cache-dtype fp8_e4m3 --mamba-ssm-dtype bfloat16 --mamba-full-memory-ratio 4.21 --mamba-radix-cache-strategy extra_buffer --max-mamba-cache-size 50 --max-running-requests 10 --context-length 262144 --reasoning-parser qwen3 --tool-call-parser qwen3_coder --sampling-defaults model --enable-metrics --enable-cache-report --host "$HOST" --port "$PORT")
volumes=(-v "$MODEL_DIR:/model:ro")
draft_parent="$(dirname "$DRAFT_DIR")"
if [[ "$(basename "$draft_parent")" == snapshots ]]; then
  draft_repo_root="$(dirname "$draft_parent")"
  draft_revision="$(basename "$DRAFT_DIR")"
  volumes+=(-v "$draft_repo_root:/draft-repo:ro")
  draft_container_path="/draft-repo/snapshots/$draft_revision"
else
  volumes+=(-v "$DRAFT_DIR:/draft:ro")
  draft_container_path=/draft
fi
args+=(--speculative-algorithm DFLASH --speculative-draft-model-path "$draft_container_path" --speculative-num-draft-tokens 8)
id=$(docker create --name "$NAME" --gpus all --ipc host --network host --cpuset-cpus "$CPUSET" --memory 110g --memory-swap 110g --label io.sxuff.qwen38.recipe=true --label "io.sxuff.qwen38.owner=$OWNER" --label "io.sxuff.qwen38.mode=$MODE" "${volumes[@]}" "$IMAGE" "${args[@]}")
python3 - "$STATE_DIR/launch.json" "$id" "$MODE" "$OWNER" "$IMAGE" "$MODEL_DIR" "$DRAFT_DIR" "${args[@]}" <<'PY'
import datetime,json,subprocess,sys
out,cid,mode,owner,image,model,draft,*args=sys.argv[1:]
d={'schema_version':1,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'container_id':cid,'mode':mode,'owner':owner,'image':image,'image_id':subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip(),'model_dir':model,'draft_dir':draft,'server_args':args}
open(out,'w').write(json.dumps(d,indent=2,sort_keys=True)+'\n')
PY
docker start "$id" >/dev/null
echo "started $NAME owner=$OWNER mode=$MODE id=$id"
