import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrimaryResultTests(unittest.TestCase):
    def test_no_spec_receipt_matches_public_comparison(self):
        receipt_path = ROOT / "evidence/huihui-nospec-study.json"
        receipt = json.loads(receipt_path.read_text())
        comparison = json.loads((ROOT / "evidence/cross-study-comparison.json").read_text())
        followup = comparison["systems"]["huihui_radixark"]["no_spec_followup"]

        self.assertEqual(
            hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            followup["summary_sha256"],
        )
        self.assertEqual(receipt["rows"], 27)
        self.assertEqual(receipt["performance_rows"], 18)
        self.assertEqual(receipt["quality_passes"], 24)
        self.assertEqual(receipt["errors"], 0)
        self.assertEqual(receipt["maximum_swap_growth_bytes"], 0)
        self.assertFalse(receipt["speculative_flags_present"])
        self.assertTrue(receipt["production_restored"])

        ratio = (
            receipt["dflash2_median_whole_request_tokens_per_second"]
            / receipt["no_spec_median_whole_request_tokens_per_second"]
        )
        self.assertAlmostEqual(ratio, receipt["dflash2_speedup_ratio"], places=12)
        self.assertAlmostEqual(
            ratio,
            comparison["derived"]["huihui_dflash2_vs_no_spec_ratio"],
            places=12,
        )

    def test_cross_arm_parity_is_explicitly_bounded(self):
        parity_path = ROOT / "evidence/huihui-cross-arm-parity.json"
        parity = json.loads(parity_path.read_text())
        comparison = json.loads((ROOT / "evidence/cross-study-comparison.json").read_text())
        receipt = comparison["parity_receipt"]
        self.assertEqual(hashlib.sha256(parity_path.read_bytes()).hexdigest(), receipt["sha256"])
        self.assertEqual(parity["rows"], 27)
        self.assertEqual(parity["normalized_payload_matches"], 27)
        self.assertEqual(parity["assembled_assistant_envelope_byte_matches"], 9)
        self.assertEqual(parity["visible_content_byte_matches"], 12)
        self.assertEqual(parity["completion_token_count_matches"], 15)
        self.assertEqual(parity["token_id_parity"], "unmeasured")
        self.assertIn("24/27", parity["claim_boundary"])
        self.assertIn("9/27", parity["claim_boundary"])

    def test_public_followup_runner_uses_no_spec_launch(self):
        script = (ROOT / "scripts/run_nospec_followup.sh").read_text()
        launch = script.split("args=(", 1)[1].split("\nid=", 1)[0]
        self.assertNotIn("--speculative-algorithm", launch)
        self.assertNotIn("--speculative-draft-model-path", launch)
        self.assertIn("--served-model-name", launch)
        self.assertIn("restore_production", script)
        self.assertIn("watchdog.py", script)
        self.assertIn("refusing to overwrite", script)

    def test_supplied_result_card_is_pinned(self):
        card = ROOT / "assets/qwen38-huihui-radixark-result.png"
        self.assertEqual(
            hashlib.sha256(card.read_bytes()).hexdigest(),
            "6809548c2548abd5d961739e04fb67fa57d4e96c0550e913894b00e51cff90b2",
        )
        self.assertFalse((ROOT / "scripts/render_card.py").exists())
        comparison = json.loads((ROOT / "evidence/cross-study-comparison.json").read_text())
        target = comparison["systems"]["huihui_radixark"]
        self.assertEqual(
            target["target"],
            "edp1096/Huihui-RadixArk-Qwen3.8-27B-abliterated-NVFP4",
        )
        self.assertEqual(
            target["target_revision"],
            "21565d389fe573a32c1c425e0c7ade204ddb2263",
        )

    def test_public_landing_pages_lead_with_primary_result(self):
        readme = (ROOT / "README.md").read_text()
        report = (ROOT / "REPORT.md").read_text()
        self.assertIn("12.31 tok/s to 57.95 tok/s", readme[:1500])
        self.assertIn("4.71×", readme[:1500])
        self.assertIn("12.31 tok/s to 57.95 tok/s", report[:1200])
        self.assertIn("4.71×", report[:1200])
        self.assertIn("evidence/promotion-report-v3.md", report)
        self.assertNotIn("acceptance", readme.lower())
        self.assertNotIn("acceptance", report.lower())
        self.assertIn(
            "github.com/sxuff/qwen38-huihui-abliterated-dflash2-dgx-spark",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
