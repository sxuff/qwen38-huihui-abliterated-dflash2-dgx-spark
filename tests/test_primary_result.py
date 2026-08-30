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

    def test_public_followup_runner_uses_no_spec_launch(self):
        script = (ROOT / "scripts/run_nospec_followup.sh").read_text()
        launch = script.split("args=(", 1)[1].split("\nid=", 1)[0]
        self.assertNotIn("--speculative-algorithm", launch)
        self.assertNotIn("--speculative-draft-model-path", launch)
        self.assertIn("--served-model-name", launch)
        self.assertIn("restore_production", script)
        self.assertIn("watchdog.py", script)
        self.assertIn("refusing to overwrite", script)

    def test_public_landing_pages_lead_with_primary_result(self):
        readme = (ROOT / "README.md").read_text()
        report = (ROOT / "REPORT.md").read_text()
        self.assertIn("12.31 tok/s to 57.95 tok/s", readme[:1500])
        self.assertIn("4.71×", readme[:1500])
        self.assertIn("12.31 tok/s to 57.95 tok/s", report[:1200])
        self.assertIn("4.71×", report[:1200])
        self.assertIn("evidence/promotion-report-v3.md", report)


if __name__ == "__main__":
    unittest.main()
