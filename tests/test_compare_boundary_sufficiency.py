import json
from pathlib import Path
import tempfile
import unittest

from regime_pilot import compare_boundary_sufficiency


class CompareBoundarySufficiencyTests(unittest.TestCase):
    def test_compare_abstract_and_clarified_metrics_and_families(self):
        baseline = {
            "n_cases": 12,
            "n_rows": 144,
            "policy_only_boundary_error_rate": 0.5,
            "policy_only_exact_action_error_rate": 0.6,
            "policy_only_decision_family_error_rate": 0.4,
            "policy_only_action_granularity_error_rate": 0.2,
            "action_granularity_rescue_rate": 0.3,
            "boundary_instability_rate": 0.75,
            "current_guidance_rescue_rate": 0.9,
            "stale_guidance_harm_rate": 0.8,
            "family_summaries": {
                "future_reform_vs_current_voting_instruction": {
                    "policy_only_boundary_error_rate": 0.4,
                    "policy_only_exact_action_error_rate": 0.5,
                    "policy_only_decision_family_error_rate": 0.3,
                    "policy_only_action_granularity_error_rate": 0.2,
                    "action_granularity_rescue_rate": 0.25,
                    "boundary_instability_rate": 0.6,
                    "current_guidance_rescue_rate": 1.0,
                    "stale_guidance_harm_rate": 1.0,
                }
            },
        }
        clarified = {
            "n_cases": 12,
            "n_rows": 144,
            "policy_only_boundary_error_rate": 0.25,
            "policy_only_exact_action_error_rate": 0.35,
            "policy_only_decision_family_error_rate": 0.1,
            "policy_only_action_granularity_error_rate": 0.25,
            "action_granularity_rescue_rate": 0.8,
            "boundary_instability_rate": 0.5,
            "current_guidance_rescue_rate": 0.4,
            "stale_guidance_harm_rate": 0.6,
            "family_summaries": {
                "future_reform_vs_current_voting_instruction": {
                    "policy_only_boundary_error_rate": 0.1,
                    "policy_only_exact_action_error_rate": 0.2,
                    "policy_only_decision_family_error_rate": 0.0,
                    "policy_only_action_granularity_error_rate": 0.2,
                    "action_granularity_rescue_rate": 1.0,
                    "boundary_instability_rate": 0.2,
                    "current_guidance_rescue_rate": 0.5,
                    "stale_guidance_harm_rate": 0.7,
                }
            },
        }

        result = compare_boundary_sufficiency.compare_analyses(
            baseline=baseline,
            candidate=clarified,
            baseline_name="abstract_full_on",
            candidate_name="clarified_full_on",
        )

        self.assertEqual(result["baseline_name"], "abstract_full_on")
        self.assertEqual(result["candidate_name"], "clarified_full_on")
        self.assertEqual(result["overall"]["policy_only_boundary_error_rate"]["delta"], -0.25)
        self.assertEqual(result["overall"]["policy_only_exact_action_error_rate"]["delta"], -0.25)
        self.assertEqual(result["overall"]["policy_only_decision_family_error_rate"]["delta"], -0.3)
        self.assertEqual(
            result["overall"]["policy_only_action_granularity_error_rate"]["delta"],
            0.05,
        )
        self.assertEqual(result["overall"]["action_granularity_rescue_rate"]["delta"], 0.5)
        self.assertEqual(result["overall"]["boundary_instability_rate"]["delta"], -0.25)
        family = result["family_comparison"]["future_reform_vs_current_voting_instruction"]
        self.assertEqual(family["policy_only_boundary_error_rate"]["delta"], -0.3)
        self.assertEqual(family["policy_only_exact_action_error_rate"]["delta"], -0.3)
        self.assertEqual(family["interpretation"], "patch_rescues_boundary_variable")

    def test_cli_writes_comparison_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            baseline_path = tmp_dir / "baseline.json"
            candidate_path = tmp_dir / "candidate.json"
            output_path = tmp_dir / "comparison.json"
            baseline_path.write_text(
                json.dumps({"policy_only_boundary_error_rate": 1.0, "family_summaries": {}}),
                encoding="utf-8",
            )
            candidate_path.write_text(
                json.dumps({"policy_only_boundary_error_rate": 0.0, "family_summaries": {}}),
                encoding="utf-8",
            )

            compare_boundary_sufficiency.main(
                [
                    "--baseline",
                    str(baseline_path),
                    "--candidate",
                    str(candidate_path),
                    "--output",
                    str(output_path),
                ]
            )

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["overall"]["policy_only_boundary_error_rate"]["delta"], -1.0)


if __name__ == "__main__":
    unittest.main()
