from pathlib import Path
import json
import tempfile
import unittest

from regime_pilot.rewrite_baselines import (
    compile_rewrite_baseline_collection,
    main,
)


SOURCE_POLICIES = {
    "election_integrity_period_v2": {
        "name": "Election Integrity Period",
        "description": "Heightened integrity period.",
        "rules": {
            "ballot_validity": (
                "False ballot validity claims are high priority. Preserve corrective "
                "education but intervene on harmful misinformation."
            ),
            "satire": (
                "Satire is allowed when clearly not deceptive. Intervene on confusing "
                "election notices."
            ),
        },
    }
}

TARGET_POLICIES = {
    "election_integrity_period_v2": {
        "name": "Election Integrity Period",
        "description": "Heightened integrity period with action-specific policy text.",
        "rules": {
            "ballot_validity": {
                "boundary_rule": "Debunking and critique remain non-removal. Endorsement crosses into intervention.",
                "action_rubric": [
                    "allow: use for ordinary critique without operational risk.",
                    "contextualize: use for clear debunking that repeats a concrete rumor.",
                    "remove: use for endorsed current false ballot-validity claims.",
                    "escalate: use for targeted mobilization based on a false ballot-validity claim.",
                ],
            },
            "satire": {
                "boundary_rule": "Obvious satire remains non-removal. Official-looking current notices cross into intervention.",
                "action_rubric": [
                    "allow: use for unmistakably fictional satire.",
                    "contextualize: use for visible parody cues with medium confusion risk.",
                    "remove: use for official-looking current closure notices.",
                    "escalate: use for coordinated deceptive notices telling voters not to vote.",
                ],
            },
        },
    }
}


def _avg_rule_chars(policies):
    lengths = []
    for policy in policies.values():
        for rule in policy["rules"].values():
            lengths.append(len(json.dumps(rule, ensure_ascii=True, sort_keys=True)))
    return sum(lengths) / len(lengths)


class RewriteBaselineTests(unittest.TestCase):
    def test_template_rewrite_outputs_runner_compatible_schema_without_case_leakage(self):
        compiled, sidecar = compile_rewrite_baseline_collection(
            SOURCE_POLICIES,
            TARGET_POLICIES,
            mode="template",
        )

        policy = compiled["election_integrity_period_v2"]
        self.assertEqual(policy["name"], "Template Rewrite Election Integrity Period")
        self.assertIsInstance(policy["description"], str)
        self.assertEqual(set(policy["rules"]), {"ballot_validity", "satire"})
        for rule_text in policy["rules"].values():
            self.assertIsInstance(rule_text, str)
            self.assertIn("Operational rewrite:", rule_text)
            self.assertIn("Decision guidance:", rule_text)

        serialized = json.dumps({"policies": compiled, "sidecar": sidecar}, sort_keys=True)
        self.assertNotIn("AG-T", serialized)
        self.assertNotIn("case_ids", serialized)
        self.assertNotIn("contrast_sets", serialized)
        self.assertFalse(sidecar["uses_cases"])
        self.assertEqual(sidecar["mode"], "template")

    def test_length_matched_rewrite_stays_close_to_target_average_without_cases(self):
        compiled, sidecar = compile_rewrite_baseline_collection(
            SOURCE_POLICIES,
            TARGET_POLICIES,
            mode="length_matched",
        )

        target_avg = _avg_rule_chars(TARGET_POLICIES)
        compiled_avg = _avg_rule_chars(compiled)

        self.assertLessEqual(compiled_avg, target_avg * 1.25)
        self.assertGreater(compiled_avg, _avg_rule_chars(SOURCE_POLICIES))
        self.assertEqual(sidecar["source_avg_rule_chars"], _avg_rule_chars(SOURCE_POLICIES))
        self.assertEqual(sidecar["target_avg_rule_chars"], target_avg)
        self.assertFalse(sidecar["uses_cases"])

    def test_cli_writes_policies_and_sidecar_without_accepting_cases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "source.json"
            target = tmp / "target.json"
            output = tmp / "rewrite.json"
            sidecar = tmp / "sidecar.json"
            source.write_text(json.dumps(SOURCE_POLICIES), encoding="utf-8")
            target.write_text(json.dumps(TARGET_POLICIES), encoding="utf-8")

            exit_code = main(
                [
                    "--source-policies",
                    str(source),
                    "--target-policies",
                    str(target),
                    "--output-policies",
                    str(output),
                    "--output-sidecar",
                    str(sidecar),
                    "--mode",
                    "length_matched",
                ]
            )

            self.assertEqual(exit_code, 0)
            written = json.loads(output.read_text(encoding="utf-8"))
            written_sidecar = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertIn("election_integrity_period_v2", written)
            self.assertEqual(written_sidecar["mode"], "length_matched")
            self.assertFalse(written_sidecar["uses_cases"])
            self.assertNotIn("case_ids", json.dumps(written_sidecar))


if __name__ == "__main__":
    unittest.main()
