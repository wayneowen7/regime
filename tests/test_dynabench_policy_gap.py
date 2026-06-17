import json
import tempfile
import unittest
from pathlib import Path

from regime_pilot.dynabench_policy_gap import (
    build_dynabench_policy_gap_artifacts,
    write_dynabench_policy_gap_artifacts,
)


class DynaBenchPolicyGapTests(unittest.TestCase):
    def test_build_artifacts_preserves_policy_case_label_in_three_policy_views(self):
        records = [
            {
                "base_id": "pass-1",
                "policy": "The assistant may disclose store hours, but must not invent discounts.",
                "transcript": "sample transcript",
                "label": "PASS",
                "metadata": json.dumps({"domain": "sales", "failure_mode": "rule_complexity"}),
            },
            {
                "base_id": "fail-1",
                "policy": "The assistant may disclose store hours, but must not invent discounts.",
                "transcript": "violating transcript",
                "label": "FAIL",
                "metadata": json.dumps({"domain": "sales", "failure_mode": "rule_complexity"}),
            },
        ]

        cases, policies, summary = build_dynabench_policy_gap_artifacts(
            records,
            sample_size=2,
            seed=7,
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(set(policies), {"abstract", "boundary", "action_rubric"})
        self.assertEqual({case["expected_decision"] for case in cases}, {"allow", "remove"})
        self.assertEqual(cases[0]["type"], "boundary_ambiguity")
        self.assertIn(cases[0]["active_regime_id"], policies["abstract"])
        self.assertIn(cases[0]["active_regime_id"], policies["boundary"])
        self.assertIn(cases[0]["active_regime_id"], policies["action_rubric"])
        pass_case = next(case for case in cases if case["post"] == "sample transcript")
        self.assertEqual(pass_case["expected_decision"], "allow")
        self.assertIn(
            "Apply the provided compliance policy",
            policies["abstract"][pass_case["active_regime_id"]]["rules"][pass_case["policy_rule"]],
        )
        self.assertIn(
            "must not invent discounts",
            policies["boundary"][pass_case["active_regime_id"]]["rules"][pass_case["policy_rule"]],
        )
        self.assertIn(
            "FAIL maps to remove",
            policies["action_rubric"][pass_case["active_regime_id"]]["rules"][pass_case["policy_rule"]],
        )
        self.assertIn(
            "PASS maps to allow",
            policies["action_rubric"][pass_case["active_regime_id"]]["rules"][pass_case["policy_rule"]],
        )
        self.assertIn(
            "Do not remove a transcript merely because the policy is strict",
            policies["action_rubric"][pass_case["active_regime_id"]]["rules"][pass_case["policy_rule"]],
        )

        serialized_summary = json.dumps(summary, ensure_ascii=False)
        self.assertFalse(summary["contains_raw_text"])
        self.assertEqual(summary["action_rubric_version"], "v2_balanced_allow_remove")
        self.assertNotIn("sample transcript", serialized_summary)
        self.assertNotIn("must not invent discounts", serialized_summary)
        self.assertEqual(summary["label_counts"], {"FAIL": 1, "PASS": 1})

    def test_write_artifacts_keeps_raw_outputs_and_text_free_summary_separate(self):
        records = [
            {
                "base_id": "pass-1",
                "policy": "Policy text belongs only in raw policy files.",
                "transcript": "Raw transcript belongs only in raw case files.",
                "label": "PASS",
                "metadata": json.dumps({"domain": "sales"}),
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = write_dynabench_policy_gap_artifacts(
                records,
                sample_size=1,
                raw_output_dir=root / "raw",
                summary_path=root / "summary.json",
            )

            case_text = (root / "raw" / "dynabench_policy_gap_cases_v0.jsonl").read_text(
                encoding="utf-8"
            )
            summary_text = (root / "summary.json").read_text(encoding="utf-8")
            self.assertIn("Raw transcript belongs only", case_text)
            self.assertNotIn("Raw transcript belongs only", summary_text)
            self.assertNotIn("Policy text belongs only", summary_text)
            self.assertFalse(summary["contains_raw_text"])
            self.assertEqual(summary["selected_count"], 1)


if __name__ == "__main__":
    unittest.main()
