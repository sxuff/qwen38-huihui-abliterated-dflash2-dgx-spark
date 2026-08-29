#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_bytes,
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    seal = json.loads((root / "preregistration.json").read_text())
    if seal.get("primary_trace_count_at_freeze") != 0:
        raise SystemExit("seal does not declare zero primary traces")

    commit = seal["source_commit"]
    git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    actual_tree = git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    if actual_tree != seal.get("source_git_tree"):
        raise SystemExit(
            f"source Git tree mismatch: expected={seal.get('source_git_tree')} actual={actual_tree}"
        )

    tracked = seal["tracked_files"]
    canonical = json.dumps(tracked, sort_keys=True, separators=(",", ":")).encode()
    canonical_sha = hashlib.sha256(canonical).hexdigest()
    if canonical_sha != seal["source_tree_sha256"]:
        raise SystemExit("source_tree_sha256 does not match tracked_files")

    for row in tracked:
        try:
            data = git(root, "show", f"{commit}:{row['path']}")
        except SystemExit as exc:
            raise SystemExit(f"sealed source file missing: {row['path']}") from exc
        if len(data) != row["bytes"]:
            raise SystemExit(f"sealed source size mismatch: {row['path']}")
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise SystemExit(f"sealed source hash mismatch: {row['path']}")
        current = root / row["path"]
        if not current.is_file():
            raise SystemExit(f"current protected source file missing: {row['path']}")
        current_data = current.read_bytes()
        if len(current_data) != row["bytes"] or hashlib.sha256(current_data).hexdigest() != row["sha256"]:
            raise SystemExit(f"current protected source differs from frozen source: {row['path']}")

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
            raise SystemExit(f"protected hash mismatch: {rel}")

    collected = root / "evidence" / "preregistration-collected.json"
    if collected.is_file():
        got = hashlib.sha256(collected.read_bytes()).hexdigest()
        if got != seal.get("collected_seal_sha256"):
            raise SystemExit("collected preregistration receipt mismatch")

    print("SEAL_OK", commit, actual_tree, seal["source_tree_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
