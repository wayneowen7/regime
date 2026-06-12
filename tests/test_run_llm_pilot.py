import json
from pathlib import Path
import unittest

from regime_pilot.run_llm_pilot import run_llm_pilot


class FakeClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def generate(self, model: str, prompt: str) -> str:
        self.calls.append({"model": model, "prompt": prompt})
        return self.response


class RunLlmPilotTests(unittest.TestCase):
    def test_run_llm_pilot_uses_client_and_summarizes_outputs(self):
        tmp_dir = Path(self.id().replace(".", "_"))
        tmp_dir.mkdir(exist_ok=True)
        policies_path = tmp_dir / "policies.json"
        precedents_path = tmp_dir / "precedents.jsonl"
        test_cases_path = tmp_dir / "test_cases.jsonl"
        try:
            policies_path.write_text(
                json.dumps(
                    {
                        "election_integrity_period_v2": {
                            "name": "Election Integrity Period",
                            "description": "Heightened integrity policy.",
                            "rules": {"voting_procedure": "Remove false voting time claims."},
                        }
                    }
                ),
                encoding="utf-8",
            )
            precedents_path.write_text(
                json.dumps(
                    {
                        "case_id": "R2-P-001",
                        "regime_id": "election_integrity_period_v2",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow not today.",
                        "decision": "remove",
                        "rationale": "False voting time.",
                        "validity_scope": "Election period.",
                        "exception_tags": [],
                        "compatible_regimes": ["election_integrity_period_v2"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            test_cases_path.write_text(
                json.dumps(
                    {
                        "case_id": "T-001",
                        "type": "within_regime_holdout",
                        "active_regime_id": "election_integrity_period_v2",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow, not today.",
                        "expected_decision": "remove",
                        "expected_rationale": "False voting time.",
                        "invalid_precedent_regimes": ["normal_civic_discussion_v1"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            client = FakeClient(
                '{"decision":"remove","rationale":"False voting time.","used_precedents":["R2-P-001"]}'
            )

            result = run_llm_pilot(
                policies_path=policies_path,
                precedents_path=precedents_path,
                test_cases_path=test_cases_path,
                client=client,
                model="fake-model",
                conditions=["regime_aware"],
                top_k=3,
                limit_cases=1,
            )

            self.assertEqual(len(client.calls), 1)
            self.assertEqual(result["summaries"]["regime_aware"]["policy_adherence_rate"], 1.0)
            self.assertEqual(result["summaries"]["regime_aware"]["mean_invalid_used_precedents"], 0.0)
        finally:
            for path in (policies_path, precedents_path, test_cases_path):
                if path.exists():
                    path.unlink()
            if tmp_dir.exists():
                tmp_dir.rmdir()

    def test_run_llm_pilot_records_operational_view_and_hides_prompt_metadata(self):
        tmp_dir = Path(self.id().replace(".", "_"))
        tmp_dir.mkdir(exist_ok=True)
        policies_path = tmp_dir / "policies.json"
        precedents_path = tmp_dir / "precedents.jsonl"
        test_cases_path = tmp_dir / "test_cases.jsonl"
        try:
            policies_path.write_text(
                json.dumps(
                    {
                        "election_integrity_period_v2": {
                            "name": "Election Integrity Period",
                            "description": "Heightened integrity policy.",
                            "rules": {"voting_procedure": "Remove false voting time claims."},
                        }
                    }
                ),
                encoding="utf-8",
            )
            precedents_path.write_text(
                json.dumps(
                    {
                        "case_id": "R2-P-001",
                        "regime_id": "election_integrity_period_v2",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow not today.",
                        "decision": "remove",
                        "rationale": "False voting time.",
                        "validity_scope": "Election period.",
                        "exception_tags": [],
                        "compatible_regimes": ["election_integrity_period_v2"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            test_cases_path.write_text(
                json.dumps(
                    {
                        "case_id": "T-001",
                        "type": "within_regime_holdout",
                        "active_regime_id": "election_integrity_period_v2",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow, not today.",
                        "expected_decision": "remove",
                        "expected_rationale": "False voting time.",
                        "invalid_precedent_regimes": ["normal_civic_discussion_v1"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            client = FakeClient(
                '{"decision":"remove","rationale":"False voting time.","used_precedents":["R2-P-001"]}'
            )

            result = run_llm_pilot(
                policies_path=policies_path,
                precedents_path=precedents_path,
                test_cases_path=test_cases_path,
                client=client,
                model="fake-model",
                conditions=["regime_aware"],
                top_k=3,
                limit_cases=1,
                memory_view="operational",
            )

            self.assertEqual(result["memory_view"], "operational")
            self.assertEqual(len(client.calls), 1)
            prompt = client.calls[0]["prompt"]
            self.assertIn("case_id: R2-P-001", prompt)
            self.assertIn("post: Polls close tomorrow not today.", prompt)
            self.assertIn("decision: remove", prompt)
            self.assertIn("rationale: False voting time.", prompt)
            self.assertNotIn("regime_id: election_integrity_period_v2", prompt)
            self.assertNotIn("validity_scope:", prompt)
            self.assertNotIn("compatible_regimes:", prompt)
            self.assertNotIn("retrieval_score:", prompt)
        finally:
            for path in (policies_path, precedents_path, test_cases_path):
                if path.exists():
                    path.unlink()
            if tmp_dir.exists():
                tmp_dir.rmdir()

    def test_run_llm_pilot_passes_stress_prompt_options_and_summarizes_stale_rationale(self):
        tmp_dir = Path(self.id().replace(".", "_"))
        tmp_dir.mkdir(exist_ok=True)
        policies_path = tmp_dir / "policies.json"
        precedents_path = tmp_dir / "precedents.jsonl"
        test_cases_path = tmp_dir / "test_cases.jsonl"
        try:
            policies_path.write_text(
                json.dumps(
                    {
                        "election_integrity_period_v2": {
                            "name": "Election Integrity Period",
                            "description": "Heightened integrity policy.",
                            "rules": {"voting_procedure": "Remove false voting time claims."},
                        }
                    }
                ),
                encoding="utf-8",
            )
            precedents_path.write_text(
                json.dumps(
                    {
                        "case_id": "R1-P-001",
                        "regime_id": "normal_civic_discussion_v1",
                        "policy_rule": "voting_procedure",
                        "post": "Polls close tomorrow not today.",
                        "decision": "contextualize",
                        "rationale": "Normal-period discussion receives context.",
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
                        "post": "Polls close tomorrow, not today.",
                        "expected_decision": "remove",
                        "expected_rationale": "False voting time.",
                        "invalid_precedent_regimes": ["normal_civic_discussion_v1"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            client = FakeClient(
                '{"decision":"contextualize","rationale":"Normal-period discussion receives context.","used_precedents":[]}'
            )

            result = run_llm_pilot(
                policies_path=policies_path,
                precedents_path=precedents_path,
                test_cases_path=test_cases_path,
                client=client,
                model="fake-model",
                conditions=["naive_memory"],
                top_k=3,
                limit_cases=1,
                memory_view="operational",
                policy_view="brief",
                stale_warning=False,
            )

            self.assertEqual(result["policy_view"], "brief")
            self.assertFalse(result["stale_warning"])
            self.assertEqual(
                result["summaries"]["naive_memory"]["mean_stale_rationale_matches"],
                1.0,
            )
            prompt = client.calls[0]["prompt"]
            self.assertIn("active_policy_focus: voting_procedure", prompt)
            self.assertNotIn("Policy rules:", prompt)
            self.assertNotIn("Remove false voting time claims.", prompt)
            self.assertNotIn("may be stale", prompt)
            self.assertNotIn("rationale still fits", prompt)
        finally:
            for path in (policies_path, precedents_path, test_cases_path):
                if path.exists():
                    path.unlink()
            if tmp_dir.exists():
                tmp_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
