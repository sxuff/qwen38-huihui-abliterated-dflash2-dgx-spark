#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

ARM = "candidate-dflash2"
EXPECTED_MODEL = "qwen38-27b-huihui-radixark-abliterated-nvfp4"


def med(values):
    xs = [float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(float(x))]
    return statistics.median(xs) if xs else None


def scrape_metrics(path: Path) -> dict:
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("#"):
            continue
        match = re.match(r"^([^\s{]+)(?:\{[^}]*\})?\s+([-+0-9.eE]+)$", line)
        if match:
            try:
                out[match.group(1)] = float(match.group(2))
            except ValueError:
                pass
    return out


def load_telemetry(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {
        "samples": len(rows),
        "minimum_mem_available_bytes": min((row["mem_available_bytes"] for row in rows), default=None),
        "maximum_swap_growth_bytes": max((row["swap_growth_bytes"] for row in rows), default=None),
    }


def load_json(path: Path):
    if not path.is_file():
        raise SystemExit(f"required evidence is missing: {path.name}")
    return json.loads(path.read_text())


def summarize_rows(rows: list[dict]) -> dict:
    perf = [row for row in rows if row.get("performance")]
    per_fixture = {}
    for fixture_id in sorted({row["fixture_id"] for row in rows}):
        group = [row for row in rows if row["fixture_id"] == fixture_id]
        per_fixture[fixture_id] = {
            "rows": len(group),
            "quality_passes": sum(bool(row.get("quality_pass")) for row in group),
            "completion_tokens": sum(int((row.get("usage") or {}).get("completion_tokens") or 0) for row in group),
            "median_ttft_seconds": med(row.get("ttft_seconds") for row in group),
            "median_end_to_end_completion_tokens_per_second": med(row.get("end_to_end_completion_tokens_per_second") for row in group),
        }
    return {
        "rows": len(rows),
        "performance_rows": len(perf),
        "quality_passes": sum(bool(row.get("quality_pass")) for row in rows),
        "completion_tokens": sum(int((row.get("usage") or {}).get("completion_tokens") or 0) for row in rows),
        "median_end_to_end_completion_tokens_per_second": med(row.get("end_to_end_completion_tokens_per_second") for row in perf),
        "per_fixture": per_fixture,
    }


def validate_lineage(repo: Path, run_root: Path, protocol: dict, runtime: dict, run: dict) -> dict:
    protocol_sha = hashlib.sha256((repo / "protocol.json").read_bytes()).hexdigest()
    fixtures_sha = hashlib.sha256((repo / "fixtures.json").read_bytes()).hexdigest()
    if run.get("arm") != ARM or run.get("protocol_sha256") != protocol_sha or run.get("fixtures_sha256") != fixtures_sha:
        raise SystemExit("candidate envelope is not bound to the frozen arm, protocol, and fixtures")

    ready = load_json(run_root / "candidate-dflash2-ready.json")
    model_ids = [row.get("id") for row in (ready.get("models") or {}).get("data") or []]
    if model_ids != [EXPECTED_MODEL] or (ready.get("canary") or {}).get("content") != "CANDIDATE_DFLASH2_READY":
        raise SystemExit("readiness receipt does not prove the exact candidate model and generation canary")

    containers = load_json(run_root / "candidate-dflash2-container.json")
    if not isinstance(containers, list) or len(containers) != 1:
        raise SystemExit("container receipt must contain exactly one inspect record")
    container = containers[0]
    labels = (container.get("Config") or {}).get("Labels") or {}
    if container.get("Image") != runtime["image_id"]:
        raise SystemExit("measured container image ID differs from the sealed runtime")
    if labels.get("io.sxuff.qwen38.recipe") != "true" or labels.get("io.sxuff.qwen38.owner") != "study" or labels.get("io.sxuff.qwen38.mode") != "dflash2":
        raise SystemExit("measured container ownership or mode labels are wrong")

    launch = load_json(run_root / "candidate-dflash2-state/launch.json")
    if launch.get("image_id") != runtime["image_id"] or launch.get("owner") != "study" or launch.get("mode") != "dflash2":
        raise SystemExit("launch receipt differs from the sealed image, owner, or mode")
    args = launch.get("server_args") or []
    if EXPECTED_MODEL not in args or "DFLASH" not in args:
        raise SystemExit("launch receipt lacks the expected served model or DFlash mode")
    model_mounts = [row for row in container.get("Mounts") or [] if row.get("Destination") == "/model"]
    if len(model_mounts) != 1 or model_mounts[0].get("Source") != launch.get("model_dir"):
        raise SystemExit("container model mount differs from the verified launch target")

    target = load_json(run_root / "candidate-dflash2-state/target-verification.json")
    draft = load_json(run_root / "candidate-dflash2-state/draft-verification.json")
    sealed_target = protocol["target"]
    sealed_draft = protocol["arms"][ARM]
    if not target.get("complete") or target.get("repository") != sealed_target["model"] or target.get("revision") != sealed_target["revision"]:
        raise SystemExit("target verification receipt differs from the sealed target")
    if not draft.get("complete") or draft.get("repository") != sealed_draft["draft_model"] or draft.get("revision") != sealed_draft["draft_revision"]:
        raise SystemExit("draft verification receipt differs from the sealed DFlash2 draft")

    if protocol["runtime_control"]["historical_and_candidate_image_id"] != runtime["image_id"]:
        raise SystemExit("protocol runtime control and runtime manifest disagree")
    return {
        "protocol_sha256": protocol_sha,
        "fixtures_sha256": fixtures_sha,
        "served_model": EXPECTED_MODEL,
        "image_id": runtime["image_id"],
        "container_id": container.get("Id"),
        "target_revision": target["revision"],
        "draft_revision": draft["revision"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    protocol = load_json(repo / "protocol.json")
    prereg = load_json(repo / "preregistration.json")
    runtime = load_json(repo / "runtime-manifest.json")
    control = load_json(repo / protocol["historical_control"]["path"])
    run = load_json(args.root / f"{ARM}.json")
    lineage = validate_lineage(repo, args.root, protocol, runtime, run)

    rows = run.get("rows") or []
    errors = run.get("errors") or []
    keys = [(row["fixture_id"], row["repetition"]) for row in rows]
    if run.get("complete") is not True or run.get("runtime_success") is not True or run.get("collection_complete") is not True:
        raise SystemExit("candidate run envelope is incomplete")
    if errors:
        raise SystemExit(f"candidate run contains {len(errors)} runtime errors")
    if len(rows) != 27 or len(set(keys)) != 27:
        raise SystemExit("candidate must contain exactly 27 unique rows")

    required_finish = set(protocol["acceptance"]["required_finish_reasons"])
    invalid_finish = [key for key, row in zip(keys, rows) if row.get("finish_reason") not in required_finish]
    invalid_usage = [key for key, row in zip(keys, rows) if int((row.get("usage") or {}).get("completion_tokens") or 0) <= 0]
    invalid_stream = [key for key, row in zip(keys, rows) if row.get("response_models") != [EXPECTED_MODEL] or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("raw_events_sha256") or "")) or int(row.get("raw_event_count") or 0) <= 0]
    perf = [row for row in rows if row.get("performance")]
    invalid_perf = [row for row in perf if not isinstance(row.get("end_to_end_completion_tokens_per_second"), (int, float)) or not math.isfinite(float(row["end_to_end_completion_tokens_per_second"])) or float(row["end_to_end_completion_tokens_per_second"]) <= 0]
    if invalid_finish or invalid_usage or invalid_stream or len(perf) != protocol["acceptance"]["required_finite_performance_rows"] or invalid_perf:
        raise SystemExit("candidate has invalid finish, usage, stream identity, or finite performance denominators")

    control_rows = {(row["fixture_id"], row["repetition"]): row for row in control["rows"]}
    if set(keys) != set(control_rows):
        raise SystemExit("candidate and historical control row keys differ")
    comparisons = []
    for row in rows:
        key = (row["fixture_id"], row["repetition"])
        old = control_rows[key]
        old_rate = old.get("end_to_end_completion_tokens_per_second")
        new_rate = row.get("end_to_end_completion_tokens_per_second")
        old_tokens = int((old.get("usage") or {}).get("completion_tokens") or 0)
        new_tokens = int((row.get("usage") or {}).get("completion_tokens") or 0)
        comparisons.append({
            "fixture_id": key[0],
            "repetition": key[1],
            "performance": bool(row.get("performance")),
            "normalized_payload_match": row.get("normalized_payload_sha256") == old.get("normalized_payload_sha256"),
            "full_payload_match": row.get("payload_sha256") == old.get("payload_sha256"),
            "exact_output_match": row.get("content_sha256") == old.get("content_sha256"),
            "completion_token_match": new_tokens == old_tokens,
            "historical_completion_tokens": old_tokens,
            "candidate_completion_tokens": new_tokens,
            "historical_control_rate": old_rate,
            "candidate_rate": new_rate,
            "speed_ratio": (new_rate / old_rate) if old_rate and new_rate else None,
            "historical_quality_pass": bool(old.get("quality_pass")),
            "candidate_quality_pass": bool(row.get("quality_pass")),
        })
    if not all(row["normalized_payload_match"] for row in comparisons):
        raise SystemExit("candidate payloads differ after removing only the required model field")

    candidate = summarize_rows(rows)
    telemetry = load_telemetry(args.root / f"{ARM}-telemetry.jsonl")
    before_metrics = scrape_metrics(args.root / f"{ARM}-metrics-before.txt")
    after_metrics = scrape_metrics(args.root / f"{ARM}-metrics-after.txt")
    verify_before = before_metrics.get("sglang:spec_verify_calls_total", 0.0)
    verify_after = after_metrics.get("sglang:spec_verify_calls_total", 0.0)
    verify_delta = verify_after - verify_before
    candidate.update({
        "errors": len(errors),
        "minimum_mem_available_bytes": telemetry["minimum_mem_available_bytes"],
        "swap_growth_bytes": telemetry["maximum_swap_growth_bytes"],
        "telemetry_samples": telemetry["samples"],
        "spec_accept_length_final": after_metrics.get("sglang:spec_accept_length"),
        "spec_accept_rate_final": after_metrics.get("sglang:spec_accept_rate"),
        "spec_verify_calls_before": verify_before,
        "spec_verify_calls_after": verify_after,
        "spec_verify_calls_delta": verify_delta,
    })

    acceptance = protocol["acceptance"]
    control_rate = float(control["median_end_to_end_completion_tokens_per_second"])
    aggregate_ratio = candidate["median_end_to_end_completion_tokens_per_second"] / control_rate
    perf_comparisons = [row for row in comparisons if row["performance"]]
    gate = {
        "lineage_bound": True,
        "operational_complete": candidate["rows"] == acceptance["complete_rows"] and candidate["errors"] <= acceptance["runtime_errors_allowed"],
        "finite_denominators_complete": len(perf) == acceptance["required_finite_performance_rows"] and not invalid_perf and len(rows) == acceptance["required_positive_completion_token_rows"],
        "response_model_identity": not invalid_stream,
        "normalized_payloads_match_historical_control": all(row["normalized_payload_match"] for row in comparisons),
        "quality_non_regression": candidate["quality_passes"] >= acceptance["minimum_quality_passes"],
        "speed_target_met": aggregate_ratio >= acceptance["minimum_median_speed_ratio_vs_historical_control"],
        "dflash_active_during_measured_rows": bool(
            verify_delta >= acceptance["minimum_measured_spec_verify_call_delta"]
            and (candidate["spec_accept_length_final"] or 0) >= acceptance["minimum_spec_accept_length"]
            and (candidate["spec_accept_rate_final"] or 0) >= acceptance["minimum_spec_accept_rate"]
        ),
        "memory_safe": bool(
            (candidate["minimum_mem_available_bytes"] or 0) >= acceptance["minimum_mem_available_bytes"]
            and (candidate["swap_growth_bytes"] or 0) <= acceptance["maximum_swap_growth_bytes"]
        ),
    }
    gate["promotion_passed"] = all(gate.values())

    summary = {
        "schema_version": 2,
        "study_id": prereg["study_id"],
        "source_commit": prereg["source_commit"],
        "source_tree_sha256": prereg["source_tree_sha256"],
        "resolved_image_id": runtime["image_id"],
        "design": protocol["design"],
        "claim_boundary": protocol["claim_boundary"],
        "lineage": lineage,
        "historical_control": {
            "target": control["target"],
            "target_revision": control["target_revision"],
            "runtime_image_id": control["runtime_image_id"],
            "median_end_to_end_completion_tokens_per_second": control_rate,
            "quality_passes": control["quality_passes"],
            "rows": control["row_count"],
            "completion_tokens": sum(int((row.get("usage") or {}).get("completion_tokens") or 0) for row in control["rows"]),
        },
        "candidate": candidate,
        "comparison": {
            "aggregate_median_speed_ratio": aggregate_ratio,
            "median_row_speed_ratio": med(row["speed_ratio"] for row in perf_comparisons),
            "exact_output_matches": sum(row["exact_output_match"] for row in comparisons),
            "completion_token_matches": sum(row["completion_token_match"] for row in comparisons),
            "normalized_payload_matches": sum(row["normalized_payload_match"] for row in comparisons),
            "full_payload_matches": sum(row["full_payload_match"] for row in comparisons),
            "rows": len(comparisons),
            "performance_rows": len(perf_comparisons),
            "rows_detail": comparisons,
        },
        "gate": gate,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    verdict = "PROMOTE" if gate["promotion_passed"] else "KEEP CURRENT"
    lines = [
        "# Huihui-RadixArk NVFP4-lm_head DFlash2 validation", "",
        f"**Promotion verdict: {verdict}.**", "",
        "One candidate arm versus a frozen historical control. Exact runtime image, fixtures, sampler, draft, and normalized payload fields match; collection sessions differ.", "",
        f"- Historical Aday DFlash2: **{control_rate:.2f} tok/s**",
        f"- Candidate DFlash2: **{candidate['median_end_to_end_completion_tokens_per_second']:.2f} tok/s**",
        f"- Historical-control ratio: **{aggregate_ratio:.2f}x**",
        f"- Automatic quality: **{candidate['quality_passes']}/{candidate['rows']} candidate** versus **{control['quality_passes']}/{control['row_count']} historical**",
        f"- Exact outputs across different targets: **{summary['comparison']['exact_output_matches']}/{summary['comparison']['rows']}**",
        f"- Completion-token count matches: **{summary['comparison']['completion_token_matches']}/{summary['comparison']['rows']}**",
        f"- Measured DFlash verification-call delta: **{verify_delta:.0f}**",
        f"- DFlash final acceptance: **{candidate['spec_accept_rate_final']} rate**, **{candidate['spec_accept_length_final']} tokens**",
        f"- Minimum MemAvailable: **{candidate['minimum_mem_available_bytes'] / 1024**3:.2f} GiB**",
        f"- Maximum swap growth: **{candidate['swap_growth_bytes']} bytes**", "",
        "## Per-fixture median whole-request tok/s", "",
        "| Fixture | Historical Aday | Candidate | Ratio |", "|---|---:|---:|---:|",
    ]
    control_per = {}
    for fixture_id in sorted({row["fixture_id"] for row in control["rows"]}):
        control_per[fixture_id] = med(row["end_to_end_completion_tokens_per_second"] for row in control["rows"] if row["fixture_id"] == fixture_id)
    for fixture_id, item in candidate["per_fixture"].items():
        old = control_per[fixture_id]
        new = item["median_end_to_end_completion_tokens_per_second"]
        ratio = new / old if old and new else None
        lines.append(f"| {fixture_id} | {old:.2f} | {new:.2f} | {ratio:.2f}x |" if ratio else f"| {fixture_id} | n/a | n/a | n/a |")
    lines += ["", "Promotion requires every preregistered lineage, denominator, model-identity, payload, speed, quality, measured-DFlash, and memory gate to pass."]
    args.report.write_text("\n".join(lines) + "\n")
    print(json.dumps({"comparison": summary["comparison"], "gate": gate}, indent=2))
    return 0 if gate["promotion_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
