import json
import tempfile
import unittest
from pathlib import Path

from regime_pilot.dataset_bootstrap import (
    build_dataset_profile,
    write_dataset_sample_outputs,
)


class DatasetBootstrapTests(unittest.TestCase):
    def test_profile_detects_policy_operation_fields_without_leaking_text(self):
        records = [
            {
                "prompt": "private prompt body should not enter the summary",
                "response": "private response body should not enter the summary",
                "safety_label": "unsafe",
                "policy": "No instructions for wrongdoing",
                "moderation_action": "refuse",
                "risk_category": "violence",
            },
            {
                "prompt": "another private prompt",
                "response": "another private response",
                "safety_label": "safe",
                "policy": "No instructions for wrongdoing",
                "moderation_action": "allow",
                "risk_category": "benign",
            },
        ]

        profile = build_dataset_profile(
            dataset_name="toy",
            dataset_id="toy/source",
            records=records,
            split_counts={"train": 2},
        )

        serialized = json.dumps(profile, ensure_ascii=False)
        self.assertNotIn("private prompt body", serialized)
        self.assertNotIn("private response body", serialized)
        self.assertFalse(profile["contains_raw_text"])
        self.assertTrue(profile["fit"]["has_text"])
        self.assertTrue(profile["fit"]["has_label"])
        self.assertTrue(profile["fit"]["has_policy"])
        self.assertTrue(profile["fit"]["has_action_signal"])
        self.assertEqual(profile["field_roles"]["prompt"], "text")
        self.assertEqual(profile["field_roles"]["safety_label"], "label")
        self.assertEqual(profile["field_roles"]["policy"], "policy")
        self.assertEqual(profile["field_roles"]["moderation_action"], "action")

    def test_write_dataset_sample_outputs_keeps_raw_and_summary_separate(self):
        records = [
            {
                "input": "raw text is allowed only in the raw sample",
                "label": "remove",
                "policy_rule": "No spam",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw" / "toy.jsonl"
            summary_path = Path(tmp) / "summary" / "toy_summary.json"
            summary = write_dataset_sample_outputs(
                dataset_name="toy",
                dataset_id="toy/source",
                records=records,
                split_counts={"train": 1},
                raw_output_path=raw_path,
                summary_output_path=summary_path,
            )

            self.assertIn("raw text is allowed", raw_path.read_text(encoding="utf-8"))
            summary_text = summary_path.read_text(encoding="utf-8")
            self.assertNotIn("raw text is allowed", summary_text)
            self.assertFalse(summary["contains_raw_text"])


if __name__ == "__main__":
    unittest.main()
