import hashlib
import importlib.util
import json
import re
import shutil
import statistics
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts/benchmark.py")
assert SPEC is not None and SPEC.loader is not None
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)
EXPECTED_MODEL = "qwen38-27b-huihui-radixark-abliterated-nvfp4"


class ContractTests(unittest.TestCase):
    def test_single_arm_protocol_is_frozen(self):
        protocol = json.loads((ROOT / "protocol.json").read_text())
        fixtures = json.loads((ROOT / "fixtures.json").read_text())["fixtures"]
        self.assertEqual(protocol["study_id"], "qwen38-huihui-radixark-abliterated-nvfp4-lmhead-dflash2-gb10-v3")
        self.assertEqual(protocol["request_contract"]["arm_order"], ["candidate-dflash2"])
        self.assertEqual(len(fixtures), 9)
        self.assertEqual(protocol["acceptance"]["complete_rows"], 27)
        self.assertEqual(protocol["acceptance"]["required_finite_performance_rows"], 18)
        self.assertEqual(protocol["acceptance"]["minimum_quality_passes"], 23)
        self.assertEqual(protocol["acceptance"]["minimum_median_speed_ratio_vs_historical_control"], 1.1)
        self.assertTrue(protocol["acceptance"]["normalized_payload_hashes_must_match_historical_control"])

    def test_candidate_inspection_is_executable_and_reproducible(self):
        receipt = json.loads((ROOT / "evidence/candidate-inspection.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.json"
            result = subprocess.run(["python3", str(ROOT / "scripts/inspect_candidate.py"), "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_text()), receipt)
        self.assertEqual(receipt["lm_head_policy"], {"quant_algo": "NVFP4", "group_size": 16})
        self.assertEqual(receipt["quantized_layer_counts"], {"FP8": 208, "NVFP4": 193})
        self.assertIn("lm_head.weight_scale_2", receipt["lm_head_index_keys"])

    def test_target_manifest_is_complete(self):
        manifest = json.loads((ROOT / "manifests/target.json").read_text())
        self.assertEqual(manifest["verified_files"], 19)
        self.assertEqual(manifest["verified_bytes"], 21945292161)
        self.assertEqual(sum(row["bytes"] for row in manifest["files"]), manifest["verified_bytes"])
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) for row in manifest["files"]))
        self.assertEqual(len({row["name"] for row in manifest["files"]}), 19)

    def test_historical_control_is_really_output_redacted(self):
        control = json.loads((ROOT / "controls/aday-dflash2-control.json").read_text())
        self.assertEqual(control["row_count"], 27)
        self.assertEqual(control["quality_passes"], 23)
        forbidden = {"content", "reasoning_content", "tool_calls", "quality_detail"}
        self.assertTrue(all(not (forbidden & set(row)) for row in control["rows"]))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", row["quality_detail_sha256"]) for row in control["rows"]))
        rates = [row["end_to_end_completion_tokens_per_second"] for row in control["rows"] if row["performance"]]
        self.assertEqual(len(rates), 18)
        self.assertAlmostEqual(statistics.median(rates), control["median_end_to_end_completion_tokens_per_second"])
        digest = hashlib.sha256((ROOT / "controls/aday-dflash2-control.json").read_bytes()).hexdigest()
        self.assertEqual(digest, json.loads((ROOT / "protocol.json").read_text())["historical_control"]["sha256"])

    def test_study_uses_exact_historical_image_and_deployment_is_separate(self):
        runtime = json.loads((ROOT / "runtime-manifest.json").read_text())
        protocol = json.loads((ROOT / "protocol.json").read_text())
        control = json.loads((ROOT / "controls/aday-dflash2-control.json").read_text())
        self.assertEqual(runtime["image_id"], control["runtime_image_id"])
        self.assertEqual(runtime["image_id"], protocol["runtime_control"]["historical_and_candidate_image_id"])
        self.assertEqual(runtime["mounted_target_revision"], protocol["target"]["revision"])
        image_control = json.loads((ROOT / "evidence/benchmark-image-control.json").read_text())
        self.assertTrue(image_control["rootfs_equal"])
        self.assertTrue(image_control["non_label_image_config_equal"])

    def test_dflash_is_the_only_serving_mode_and_rollback_is_canaried(self):
        serve = (ROOT / "scripts/serve.sh").read_text()
        runner = (ROOT / "scripts/run_study.sh").read_text()
        watchdog = (ROOT / "scripts/watchdog.py").read_text()
        self.assertIn("MODE=dflash2", serve)
        self.assertIn("--speculative-algorithm DFLASH", serve)
        self.assertIn("--speculative-num-draft-tokens 8", serve)
        self.assertIn("--arm candidate-dflash2", runner)
        self.assertNotIn("run_arm no-spec", runner)
        self.assertIn("PRE_STUDY_SERVICE_OK", runner)
        self.assertIn("RESTORED_AFTER_CANDIDATE", runner)
        self.assertIn("--owner \"$OWNER\"", runner)
        self.assertIn("exact recipe and owner labels", watchdog)

    def test_dead_endpoint_collector_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "dead.json"
            result = subprocess.run([
                "python3", str(ROOT / "scripts/benchmark.py"), "--arm", "candidate-dflash2",
                "--protocol", str(ROOT / "protocol.json"), "--fixtures", str(ROOT / "fixtures.json"),
                "--base-url", "http://127.0.0.1:9/v1", "--output", str(out),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            envelope = json.loads(out.read_text())
            self.assertFalse(envelope["complete"])
            self.assertEqual(len(envelope["rows"]), 27)
            self.assertEqual(len(envelope["errors"]), 27)

    def test_quality_scorers_reject_substrings_and_bad_prose(self):
        fixtures = {row["id"]: row for row in json.loads((ROOT / "fixtures.json").read_text())["fixtures"]}
        passed, _ = benchmark.score(fixtures["math"], {"content": "The intermediate value is 4080, not the answer.", "tool_calls": []})
        self.assertFalse(passed)
        passed, _ = benchmark.score(fixtures["prose"], {"content": "A generic paragraph with words but none of the required facts about the artifact.", "tool_calls": []})
        self.assertFalse(passed)

    def _write_candidate_run(self, root: Path, speed_factor: float, extra_quality_failures: int = 0, wrong_model: bool = False, missing_rate: bool = False, zero_delta: bool = False):
        control = json.loads((ROOT / "controls/aday-dflash2-control.json").read_text())
        protocol = json.loads((ROOT / "protocol.json").read_text())
        runtime = json.loads((ROOT / "runtime-manifest.json").read_text())
        rows = []
        remaining = extra_quality_failures
        for old in control["rows"]:
            row = dict(old)
            row["arm"] = "candidate-dflash2"
            row["payload_sha256"] = "candidate-model-field-intentionally-differs"
            row["end_to_end_completion_tokens_per_second"] *= speed_factor
            row["response_models"] = ["wrong-model" if wrong_model else EXPECTED_MODEL]
            row["raw_event_count"] = 1
            row["raw_events_sha256"] = "a" * 64
            if remaining and row["quality_pass"]:
                row["quality_pass"] = False
                remaining -= 1
            rows.append(row)
        if missing_rate:
            next(row for row in rows if row["performance"])["end_to_end_completion_tokens_per_second"] = None
        envelope = {
            "arm": "candidate-dflash2", "complete": True, "runtime_success": True, "collection_complete": True,
            "errors": [], "rows": rows,
            "protocol_sha256": hashlib.sha256((ROOT / "protocol.json").read_bytes()).hexdigest(),
            "fixtures_sha256": hashlib.sha256((ROOT / "fixtures.json").read_bytes()).hexdigest(),
        }
        (root / "candidate-dflash2.json").write_text(json.dumps(envelope) + "\n")
        (root / "candidate-dflash2-metrics-before.txt").write_text("sglang:spec_verify_calls_total 2\n")
        after_calls = 2 if zero_delta else 29
        (root / "candidate-dflash2-metrics-after.txt").write_text(f"sglang:spec_accept_length 5\nsglang:spec_accept_rate 0.7\nsglang:spec_verify_calls_total {after_calls}\n")
        (root / "candidate-dflash2-telemetry.jsonl").write_text(json.dumps({"mem_available_bytes": 20 * 1024**3, "swap_growth_bytes": 0}) + "\n")
        (root / "candidate-dflash2-ready.json").write_text(json.dumps({"models": {"data": [{"id": EXPECTED_MODEL}]}, "canary": {"content": "CANDIDATE_DFLASH2_READY"}}))
        (root / "candidate-dflash2-container.json").write_text(json.dumps([{"Id": "container-id", "Image": runtime["image_id"], "Config": {"Labels": {"io.sxuff.qwen38.recipe": "true", "io.sxuff.qwen38.owner": "study", "io.sxuff.qwen38.mode": "dflash2"}}, "Mounts": [{"Destination": "/model", "Source": "/modeldir"}]}]))
        state = root / "candidate-dflash2-state"
        state.mkdir()
        (state / "launch.json").write_text(json.dumps({"image_id": runtime["image_id"], "owner": "study", "mode": "dflash2", "model_dir": "/modeldir", "server_args": [EXPECTED_MODEL, "DFLASH"]}))
        (state / "target-verification.json").write_text(json.dumps({"complete": True, "repository": protocol["target"]["model"], "revision": protocol["target"]["revision"]}))
        arm = protocol["arms"]["candidate-dflash2"]
        (state / "draft-verification.json").write_text(json.dumps({"complete": True, "repository": arm["draft_model"], "revision": arm["draft_revision"]}))

    def _analyze(self, root: Path):
        summary = root / "summary.json"
        report = root / "REPORT.md"
        result = subprocess.run(["python3", str(ROOT / "scripts/analyze.py"), "--root", str(root), "--output", str(summary), "--report", str(report)], capture_output=True, text=True)
        return result, summary

    def test_analyzer_passes_only_all_frozen_gates(self):
        if not (ROOT / "preregistration.json").is_file():
            self.skipTest("preregistration not generated yet")
        for factor, failures, should_pass in [(1.20, 0, True), (1.05, 0, False), (1.20, 1, False)]:
            with self.subTest(factor=factor, failures=failures), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self._write_candidate_run(root, factor, failures)
                result, summary = self._analyze(root)
                self.assertEqual(result.returncode == 0, should_pass, result.stderr)
                self.assertEqual(json.loads(summary.read_text())["gate"]["promotion_passed"], should_pass)

    def test_analyzer_rejects_wrong_model_missing_rate_and_no_measured_dflash_delta(self):
        if not (ROOT / "preregistration.json").is_file():
            self.skipTest("preregistration not generated yet")
        for kwargs in ({"wrong_model": True}, {"missing_rate": True}, {"zero_delta": True}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self._write_candidate_run(root, 1.20, **kwargs)
                result, summary = self._analyze(root)
                self.assertNotEqual(result.returncode, 0)
                if kwargs.get("zero_delta"):
                    self.assertFalse(json.loads(summary.read_text())["gate"]["promotion_passed"])
                else:
                    self.assertFalse(summary.exists())

    def test_artifact_verifier_rejects_extra_file(self):
        manifest = json.loads((ROOT / "manifests/draft.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mf = root / "manifest.json"
            mf.write_text(json.dumps({"schema_version": 1, "repository": manifest["repository"], "revision": manifest["revision"], "files": []}))
            (root / "unexpected").write_text("x")
            result = subprocess.run(["python3", str(ROOT / "scripts/verify_artifacts.py"), "--manifest", str(mf), "--root", str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_current_protected_source_must_match_frozen_source(self):
        if not (ROOT / "preregistration.json").is_file():
            self.skipTest("preregistration not generated yet")
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("private", "__pycache__"))
            ok = subprocess.run(["python3", str(copy / "scripts/verify_seal.py")], capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            with (copy / "scripts/benchmark.py").open("a") as handle:
                handle.write("\n# tampered after freeze\n")
            bad = subprocess.run(["python3", str(copy / "scripts/verify_seal.py")], capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("current protected source differs", bad.stderr)

    def test_apache_notice_is_distributed(self):
        notice = (ROOT / "NOTICE").read_text()
        license_text = (ROOT / "THIRD_PARTY_LICENSES/Apache-2.0.txt").read_text()
        self.assertIn("Apache License", license_text)
        for row in json.loads((ROOT / "runtime-manifest.json").read_text())["overlay_files"]:
            self.assertIn("docker/" + row["path"], notice)


if __name__ == "__main__":
    unittest.main()
