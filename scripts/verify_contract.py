#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from verify_seal import main as verify_historical_seal


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    verify_historical_seal()

    seal = json.loads((root / "preregistration.json").read_text())
    protected = {
        "protocol.json": "protocol_sha256",
        "fixtures.json": "fixtures_sha256",
        "manifests/target.json": "target_manifest_sha256",
        "manifests/draft.json": "draft_manifest_sha256",
        "runtime-manifest.json": "runtime_manifest_sha256",
    }
    for rel, key in protected.items():
        got = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        if got != seal[key]:
            raise SystemExit(f"protected contract mismatch: {rel}")

    runtime = json.loads((root / "runtime-manifest.json").read_text())
    if runtime["image_id"] != seal["resolved_image_id"]:
        raise SystemExit("resolved image ID mismatch")

    if os.environ.get("QWEN38_ALLOW_DIRTY") != "1":
        unstaged = subprocess.run(
            ["git", "-C", str(root), "diff", "--quiet", "--"],
            capture_output=True,
        )
        staged = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--quiet", "--"],
            capture_output=True,
        )
        if unstaged.returncode != 0 or staged.returncode != 0:
            raise SystemExit(
                "working tree has tracked modifications; commit/revert them or set QWEN38_ALLOW_DIRTY=1 for an explicitly unsealed local experiment"
            )

    print("RUNTIME_CONTRACT_OK", seal["study_id"], runtime["image_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
