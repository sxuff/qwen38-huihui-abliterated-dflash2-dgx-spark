#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${MODEL_DIR:?set MODEL_DIR to the pinned candidate snapshot}"
DRAFT="${DRAFT_DIR:?set DRAFT_DIR to the pinned DFlash2 draft snapshot}"
IMAGE="${IMAGE:-sxuff/qwen38-27b-abliterated-dflash2:2026-08-29}"
RUN_ROOT="${RUN_ROOT:-$ROOT/private/primary}"
NAME="${STUDY_CONTAINER_NAME:-qwen38-huihui-radixark-nvfp4-study}"
OWNER=study
OLD_MODEL_UNIT="${OLD_MODEL_UNIT:-qwen38-abliterated-dflash2.service}"
OLD_PROXY_UNIT="${OLD_PROXY_UNIT:-qwen38-abliterated-dflash2-proxy.service}"
OLD_MODEL_ID="${OLD_MODEL_ID:-qwen38-27b-ara-abliterated-nvfp4-mtp}"
RESTORE_KEY_FILE="${RESTORE_KEY_FILE:-$HOME/.config/qwen38/proxy.key}"
RESTORE_TIMEOUT_SECONDS="${RESTORE_TIMEOUT_SECONDS:-900}"
RESTORED=0
WATCHDOG_PID=""
mkdir -p "$RUN_ROOT/candidate-dflash2-state"
python3 "$ROOT/scripts/verify_contract.py" >/dev/null
python3 "$ROOT/scripts/verify_artifacts.py" --manifest "$ROOT/manifests/target.json" --root "$TARGET" --report "$RUN_ROOT/candidate-dflash2-state/target-verification.json" >/dev/null
python3 "$ROOT/scripts/verify_artifacts.py" --manifest "$ROOT/manifests/draft.json" --root "$DRAFT" --report "$RUN_ROOT/candidate-dflash2-state/draft-verification.json" >/dev/null

cleanup_candidate() {
  if [[ -n "$WATCHDOG_PID" ]]; then
    touch "$RUN_ROOT/candidate-dflash2-stop" || true
    wait "$WATCHDOG_PID" 2>/dev/null || true
    WATCHDOG_PID=""
  fi
  NAME="$NAME" OWNER="$OWNER" "$ROOT/scripts/stop.sh" >/dev/null 2>&1 || true
}

restore_previous() {
  [[ "$RESTORED" == 0 ]] || return 0
  RESTORED=1
  cleanup_candidate
  systemctl --user start "$OLD_MODEL_UNIT" "$OLD_PROXY_UNIT"
  python3 "$ROOT/scripts/wait_endpoint.py" \
    --base-url http://172.17.0.1:8001 \
    --expected-model "$OLD_MODEL_ID" \
    --api-key-file "$RESTORE_KEY_FILE" \
    --timeout-seconds "$RESTORE_TIMEOUT_SECONDS" \
    --canary-prompt 'Reply with exactly RESTORED_AFTER_CANDIDATE' \
    --canary-expected RESTORED_AFTER_CANDIDATE \
    > "$RUN_ROOT/restored-service.json"
}

on_exit() {
  status=$?
  trap - EXIT INT TERM
  restore_previous || status=$?
  exit "$status"
}
trap on_exit EXIT INT TERM

systemctl --user is-active --quiet "$OLD_MODEL_UNIT"
systemctl --user is-active --quiet "$OLD_PROXY_UNIT"
python3 "$ROOT/scripts/wait_endpoint.py" \
  --base-url http://172.17.0.1:8001 \
  --expected-model "$OLD_MODEL_ID" \
  --api-key-file "$RESTORE_KEY_FILE" \
  --timeout-seconds 120 \
  --canary-prompt 'Reply with exactly PRE_STUDY_SERVICE_OK' \
  --canary-expected PRE_STUDY_SERVICE_OK \
  > "$RUN_ROOT/pre-study-service.json"
systemctl --user stop "$OLD_PROXY_UNIT" "$OLD_MODEL_UNIT"
cleanup_candidate
rm -f "$RUN_ROOT/candidate-dflash2-stop" "$RUN_ROOT/candidate-dflash2-incident.json"
baseline_swap=$(awk '/^SwapTotal:/ {t=$2} /^SwapFree:/ {f=$2} END {printf "%.0f", (t-f)*1024}' /proc/meminfo)
MODEL_DIR="$TARGET" DRAFT_DIR="$DRAFT" IMAGE="$IMAGE" NAME="$NAME" OWNER="$OWNER" PORT=8001 STATE_DIR="$RUN_ROOT/candidate-dflash2-state" "$ROOT/scripts/serve.sh"
python3 "$ROOT/scripts/wait_endpoint.py" \
  --base-url http://127.0.0.1:8001 \
  --expected-model qwen38-27b-huihui-radixark-abliterated-nvfp4 \
  --timeout-seconds 900 \
  --canary-prompt 'Reply with exactly CANDIDATE_DFLASH2_READY' \
  --canary-expected CANDIDATE_DFLASH2_READY \
  > "$RUN_ROOT/candidate-dflash2-ready.json"
docker inspect "$NAME" > "$RUN_ROOT/candidate-dflash2-container.json"
curl -fsS http://127.0.0.1:8001/metrics > "$RUN_ROOT/candidate-dflash2-metrics-before.txt"
python3 "$ROOT/scripts/watchdog.py" --output "$RUN_ROOT/candidate-dflash2-telemetry.jsonl" --stop "$RUN_ROOT/candidate-dflash2-stop" --incident "$RUN_ROOT/candidate-dflash2-incident.json" --container "$NAME" --owner "$OWNER" --baseline-swap "$baseline_swap" &
WATCHDOG_PID=$!
python3 "$ROOT/scripts/benchmark.py" --arm candidate-dflash2 --protocol "$ROOT/protocol.json" --fixtures "$ROOT/fixtures.json" --base-url http://127.0.0.1:8001/v1 --output "$RUN_ROOT/candidate-dflash2.json"
curl -fsS http://127.0.0.1:8001/metrics > "$RUN_ROOT/candidate-dflash2-metrics-after.txt"
touch "$RUN_ROOT/candidate-dflash2-stop"
wait "$WATCHDOG_PID"
WATCHDOG_PID=""
docker logs "$NAME" > "$RUN_ROOT/candidate-dflash2-server.log" 2>&1
NAME="$NAME" OWNER="$OWNER" "$ROOT/scripts/stop.sh"
set +e
python3 "$ROOT/scripts/analyze.py" --root "$RUN_ROOT" --output "$ROOT/results/summary.json" --report "$ROOT/REPORT.md"
analyze_status=$?
set -e
restore_previous
trap - EXIT INT TERM
if [[ "$analyze_status" -ne 0 ]]; then
  echo "candidate failed a frozen promotion gate; current service restored" >&2
  exit "$analyze_status"
fi
echo "CANDIDATE_DFLASH2_STUDY_PASS"
