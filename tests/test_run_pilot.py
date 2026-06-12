import json
from pathlib import Path
import unittest

from regime_pilot.run_pilot import run_pilot


class RunPilotTests(unittest.TestCase):
    def test_run_pilot_returns_condition_summaries(self):
        tmp_dir = Path(self.id().replace(".", "_"))
        tmp_dir.mkdir(exist_ok=True)
        policies_path = tmp_dir / "policies.json"
        precedents_path = tmp_dir / "precedents.jsonl"
        test_cases_path = tmp_dir / "test_cases.jsonl"
        try:
            policies_path.write_text("{}", encoding="utf-8")
            precedents_path.write_text(
                json.dumps(
                    {
                        "case_id": "R1-P-001",
                        "regime_id": "normal_civic_discussion_v1",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow not today.",
                        "decision": "contextualize",
                        "rationale": "Normal period contextualization.",
                        "validity_scope": "Normal civic discussion only.",
                        "exception_tags": [],
                        "compatible_regimes": ["normal_civic_discussion_v1"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            test_cases_path.write_text(
                json.dumps(
                    {
                        "case_id": "T-001",
                        "type": "cross_regime_conflict",
                        "active_regime_id": "election_integrity_period_v2",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow not today.",
                        "expected_decision": "remove",
                        "expected_rationale": "False voting time.",
                        "invalid_precedent_regimes": ["normal_civic_discussion_v1"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = run_pilot(
                policies_path=policies_path,
                precedents_path=precedents_path,
                test_cases_path=test_cases_path,
                top_k=3,
            )

            self.assertIn("naive_memory", result["summaries"])
            self.assertEqual(
                result["summaries"]["naive_memory"]["mean_invalid_activation_rate"],
                1.0,
            )
            self.assertEqual(
                result["summaries"]["policy_only"]["mean_invalid_activation_rate"],
                0.0,
            )
        finally:
            for path in (policies_path, precedents_path, test_cases_path):
                if path.exists():
                    path.unlink()
            if tmp_dir.exists():
                tmp_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
