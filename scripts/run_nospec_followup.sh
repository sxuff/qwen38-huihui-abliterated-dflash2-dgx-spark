#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Run the Huihui-RadixArk no-spec follow-up against the checked-in DFlash2 result.

Required:
  MODEL_DIR=/path/to/pinned/target/snapshot

Optional:
  IMAGE=sxuff/qwen38-27b-abliterated-dflash2:2026-08-29
  RUN_ROOT=$PWD/private/no-spec-followup
  CURRENT_MODEL_UNIT=qwen38-huihui-radixark-dflash2.service
  CURRENT_PROXY_UNIT=qwen38-huihui-radixark-dflash2-proxy.service
  PROXY_KEY_FILE=$HOME/.config/qwen38/proxy.key
  RESTORE_PRODUCTION=1
EOF
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="${MODEL_DIR:?set MODEL_DIR to the pinned Huihui-RadixArk snapshot}"
IMAGE="${IMAGE:-sxuff/qwen38-27b-abliterated-dflash2:2026-08-29}"
EXPECTED_IMAGE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image_id"])' "$ROOT/runtime-manifest.json")"
MODEL="qwen38-27b-huihui-radixark-abliterated-nvfp4"
RUN_ROOT="${RUN_ROOT:-$ROOT/private/no-spec-followup}"
NAME="${NAME:-qwen38-huihui-radixark-nospec-study}"
OWNER="${OWNER:-study:qwen38-huihui-radixark-nospec}"
CURRENT_MODEL_UNIT="${CURRENT_MODEL_UNIT:-qwen38-huihui-radixark-dflash2.service}"
CURRENT_PROXY_UNIT="${CURRENT_PROXY_UNIT:-qwen38-huihui-radixark-dflash2-proxy.service}"
PROXY_KEY_FILE="${PROXY_KEY_FILE:-$HOME/.config/qwen38/proxy.key}"
RESTORE_PRODUCTION="${RESTORE_PRODUCTION:-1}"
STOP_FILE="$RUN_ROOT/watchdog.stop"
INCIDENT_FILE="$RUN_ROOT/watchdog-incident.json"
WATCHDOG_PID=""
DISPLACED=0
RESTORED=0

mkdir -p "$RUN_ROOT"
[[ ! -e "$RUN_ROOT/RESULT.json" ]] || { echo "refusing to overwrite $RUN_ROOT/RESULT.json" >&2; exit 2; }
rm -f "$STOP_FILE" "$INCIDENT_FILE"

owned_remove() {
  if ! docker inspect "$NAME" >/dev/null 2>&1; then
    return 0
  fi
  local actual_owner
  actual_owner="$(docker inspect -f '{{index .Config.Labels "io.sxuff.qwen38.owner"}}' "$NAME" 2>/dev/null || true)"
  [[ "$actual_owner" == "$OWNER" ]] || { echo "refusing to remove $NAME owned by ${actual_owner:-unset}" >&2; return 2; }
  docker rm -f "$NAME" >/dev/null
}

restore_production() {
  local rc=0
  if [[ -n "$WATCHDOG_PID" ]] && kill -0 "$WATCHDOG_PID" 2>/dev/null; then
    touch "$STOP_FILE"
    wait "$WATCHDOG_PID" || rc=1
  fi
  WATCHDOG_PID=""
  owned_remove || rc=1
  if [[ "$DISPLACED" -eq 1 && "$RESTORE_PRODUCTION" == 1 ]]; then
    systemctl --user start "$CURRENT_MODEL_UNIT" "$CURRENT_PROXY_UNIT" || rc=1
    if [[ -f "$PROXY_KEY_FILE" ]] && python3 "$ROOT/scripts/wait_endpoint.py" \
        --base-url http://172.17.0.1:8001 \
        --expected-model "$MODEL" \
        --api-key-file "$PROXY_KEY_FILE" \
        --timeout-seconds 1200 \
        --canary-prompt "Reply with exactly HUIHUI_DFLASH2_RESTORED" \
        --canary-expected HUIHUI_DFLASH2_RESTORED \
        > "$RUN_ROOT/restored.json"; then
      RESTORED=1
    else
      rc=1
    fi
  else
    RESTORED=1
  fi
  return "$rc"
}

on_exit() {
  local rc=$?
  trap - EXIT INT TERM
  if [[ "$RESTORED" -ne 1 ]]; then
    restore_production || rc=90
  fi
  exit "$rc"
}
trap on_exit EXIT INT TERM

python3 "$ROOT/scripts/verify_contract.py" > "$RUN_ROOT/contract.txt"
python3 "$ROOT/scripts/verify_artifacts.py" \
  --manifest "$ROOT/manifests/target.json" \
  --root "$MODEL_DIR" \
  --report "$RUN_ROOT/target-verification.json" \
  > "$RUN_ROOT/target-verification.txt"
actual_image="$(docker image inspect "$IMAGE" --format '{{.Id}}')"
[[ "$actual_image" == "$EXPECTED_IMAGE" ]] || { echo "image mismatch: expected=$EXPECTED_IMAGE actual=$actual_image" >&2; exit 2; }

model_active="$(systemctl --user is-active "$CURRENT_MODEL_UNIT" 2>/dev/null || true)"
proxy_active="$(systemctl --user is-active "$CURRENT_PROXY_UNIT" 2>/dev/null || true)"
if [[ "$model_active" == active || "$proxy_active" == active ]]; then
  [[ "$model_active" == active && "$proxy_active" == active ]] || { echo "production units are only partially active" >&2; exit 2; }
  [[ -f "$PROXY_KEY_FILE" ]] || { echo "active production service requires PROXY_KEY_FILE" >&2; exit 2; }
  python3 "$ROOT/scripts/wait_endpoint.py" \
    --base-url http://172.17.0.1:8001 \
    --expected-model "$MODEL" \
    --api-key-file "$PROXY_KEY_FILE" \
    --timeout-seconds 60 \
    --canary-prompt "Reply with exactly HUIHUI_DFLASH2_BEFORE_NOSPEC" \
    --canary-expected HUIHUI_DFLASH2_BEFORE_NOSPEC \
    > "$RUN_ROOT/displaced.json"
  systemctl --user stop "$CURRENT_PROXY_UNIT" "$CURRENT_MODEL_UNIT"
  DISPLACED=1
fi

owned_remove
baseline_swap="$(python3 - <<'PY'
from pathlib import Path
values={}
for line in Path('/proc/meminfo').read_text().splitlines():
    key,raw=line.split(':',1); values[key]=int(raw.strip().split()[0])*1024
print(values['SwapTotal']-values['SwapFree'])
PY
)"

python3 - "$ROOT/protocol.json" "$RUN_ROOT/protocol-nospec.json" <<'PY'
import json,sys
source,output=sys.argv[1:]
data=json.load(open(source))
data['design']='same Huihui target and qualified runtime with speculative decoding disabled'
data['arms']['candidate-no-spec']={'speculation':'disabled','runtime_base_commit':data['arms']['candidate-dflash2']['runtime_base_commit']}
data['request_contract']['arm_order']=['candidate-no-spec']
json.dump(data,open(output,'w'),indent=2,sort_keys=True); open(output,'a').write('\n')
PY

args=(
  python3 -m sglang.launch_server --trust-remote-code
  --model-path /model --served-model-name "$MODEL"
  --mem-fraction-static 0.70 --attention-backend flashinfer
  --chunked-prefill-size 8192 --disable-prefill-cuda-graph
  --kv-cache-dtype fp8_e4m3 --mamba-ssm-dtype bfloat16
  --mamba-full-memory-ratio 4.21 --mamba-radix-cache-strategy extra_buffer
  --max-mamba-cache-size 50 --max-running-requests 10 --context-length 262144
  --reasoning-parser qwen3 --tool-call-parser qwen3_coder --sampling-defaults model
  --enable-metrics --enable-cache-report --host 127.0.0.1 --port 8001
)

id="$(docker create --name "$NAME" --gpus all --ipc host --network host \
  --cpuset-cpus 5-9,15-19 --memory 110g --memory-swap 110g \
  --label io.sxuff.qwen38.recipe=true \
  --label "io.sxuff.qwen38.owner=$OWNER" \
  --label io.sxuff.qwen38.mode=no-spec \
  -v "$MODEL_DIR:/model:ro" "$IMAGE" "${args[@]}")"
docker inspect "$NAME" > "$RUN_ROOT/container.json"
python3 - "$RUN_ROOT/launch.json" "$id" "$actual_image" "$MODEL_DIR" "${args[@]}" <<'PY'
import json,sys
out,cid,image,model,*args=sys.argv[1:]
json.dump({'schema_version':1,'container_id':cid,'image_id':image,'model_dir':model,'mode':'no-spec','server_args':args},open(out,'w'),indent=2,sort_keys=True); open(out,'a').write('\n')
PY

docker start "$id" >/dev/null
python3 "$ROOT/scripts/watchdog.py" \
  --output "$RUN_ROOT/telemetry.jsonl" --stop "$STOP_FILE" --incident "$INCIDENT_FILE" \
  --container "$NAME" --owner "$OWNER" --baseline-swap "$baseline_swap" &
WATCHDOG_PID=$!
python3 "$ROOT/scripts/wait_endpoint.py" \
  --base-url http://127.0.0.1:8001 --expected-model "$MODEL" --timeout-seconds 1200 \
  --canary-prompt "Reply with exactly HUIHUI_NOSPEC_READY" --canary-expected HUIHUI_NOSPEC_READY \
  > "$RUN_ROOT/ready.json"
curl -fsS http://127.0.0.1:8001/metrics > "$RUN_ROOT/metrics-before.txt"
SANDBOX_IMAGE="$IMAGE" python3 "$ROOT/scripts/benchmark.py" \
  --arm candidate-no-spec --protocol "$RUN_ROOT/protocol-nospec.json" \
  --fixtures "$ROOT/fixtures.json" --base-url http://127.0.0.1:8001/v1 \
  --output "$RUN_ROOT/candidate-no-spec.json" > "$RUN_ROOT/benchmark-summary.json"
curl -fsS http://127.0.0.1:8001/metrics > "$RUN_ROOT/metrics-after.txt"
touch "$STOP_FILE"
wait "$WATCHDOG_PID"
WATCHDOG_PID=""
[[ ! -e "$INCIDENT_FILE" ]] || { echo "memory watchdog incident" >&2; exit 2; }

python3 - "$RUN_ROOT" "$ROOT/results/summary.json" <<'PY'
import json,math,statistics,sys
from pathlib import Path
root=Path(sys.argv[1]); dflash=json.load(open(sys.argv[2])); run=json.load(open(root/'candidate-no-spec.json'))
rows=run['rows']; perf=[row for row in rows if row.get('performance')]
assert run.get('complete') is True and not run.get('errors') and len(rows)==27 and len(perf)==18
assert all(math.isfinite(float(row['end_to_end_completion_tokens_per_second'])) and row['end_to_end_completion_tokens_per_second']>0 for row in perf)
container=json.load(open(root/'container.json'))[0]; cmd=container['Config']['Cmd']
assert '--speculative-algorithm' not in cmd and '--speculative-draft-model-path' not in cmd
telemetry=[json.loads(line) for line in (root/'telemetry.jsonl').read_text().splitlines() if line.strip()]
no_spec=statistics.median(row['end_to_end_completion_tokens_per_second'] for row in perf)
dflash_rate=float(dflash['candidate']['median_end_to_end_completion_tokens_per_second'])
summary={
 'schema_version':1,'study':'matched_huihui_no_spec_vs_qualified_dflash2',
 'model':'qwen38-27b-huihui-radixark-abliterated-nvfp4','image_id':container['Image'],
 'fixtures_sha256':run['fixtures_sha256'],'protocol_sha256':run['protocol_sha256'],
 'rows':len(rows),'performance_rows':len(perf),'quality_passes':sum(bool(row.get('quality_pass')) for row in rows),
 'errors':len(run.get('errors') or []),'no_spec_median_whole_request_tokens_per_second':no_spec,
 'dflash2_median_whole_request_tokens_per_second':dflash_rate,'dflash2_speedup_ratio':dflash_rate/no_spec,
 'minimum_mem_available_bytes':min(row['mem_available_bytes'] for row in telemetry),
 'maximum_swap_growth_bytes':max(row['swap_growth_bytes'] for row in telemetry),
 'speculative_flags_present':False,
}
json.dump(summary,open(root/'no-spec-summary.json','w'),indent=2,sort_keys=True); open(root/'no-spec-summary.json','a').write('\n')
PY

restore_production
python3 - "$RUN_ROOT/no-spec-summary.json" "$RUN_ROOT/RESULT.json" "$RESTORED" <<'PY'
import json,sys
summary,out,restored=sys.argv[1:]
data=json.load(open(summary)); data['production_restored']=restored=='1'
json.dump(data,open(out,'w'),indent=2,sort_keys=True); open(out,'a').write('\n')
print(json.dumps(data,sort_keys=True))
PY
trap - EXIT INT TERM
