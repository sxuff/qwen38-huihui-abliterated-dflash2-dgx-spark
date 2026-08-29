#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py'
python3 -m py_compile "$ROOT"/scripts/*.py
for f in "$ROOT"/scripts/*.sh; do bash -n "$f"; done
python3 - "$ROOT" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
for path in sorted(root.rglob('*.json')):
    if any(part in {'.git','private','__pycache__'} for part in path.parts):
        continue
    json.loads(path.read_text())
PY
tmp_receipt="$(mktemp)"
python3 "$ROOT/scripts/inspect_candidate.py" --output "$tmp_receipt" >/dev/null
cmp "$tmp_receipt" "$ROOT/evidence/candidate-inspection.json"
rm "$tmp_receipt"
if [[ -f "$ROOT/preregistration.json" ]]; then
  python3 "$ROOT/scripts/verify_seal.py" >/dev/null
  python3 "$ROOT/scripts/verify_contract.py" >/dev/null
fi
python3 - "$ROOT" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); runtime=json.loads((root/'runtime-manifest.json').read_text())
for row in runtime['overlay_files']:
    path=root/'docker'/row['path']
    assert path.stat().st_size==row['bytes'], path
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'], path
PY
git -C "$ROOT" diff --check
echo REPOSITORY_CHECKS_OK
