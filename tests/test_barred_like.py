import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from regime_pilot import barred_like


class QueueClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate(self, model: str, prompt: str) -> str:
        self.calls.append({"model": model, "prompt": prompt})
        return self.responses.pop(0)


class BarredLikeTests(unittest.TestCase):
    def test_parse_json_list_extracts_fenced_array(self):
        parsed = barred_like.parse_json_list(
            """Diagnostic output:
```json
[
  {"content": "A boundary case.", "proposed_label": "restrict"}
]
```"""
        )

        self.assertEqual(parsed, [{"content": "A boundary case.", "proposed_label": "restrict"}])

    def test_parse_json_list_accepts_single_object_as_singleton_candidate(self):
        parsed = barred_like.parse_json_list(
            '{"content": "A boundary case.", "proposed_label": "restrict"}'
        )

        self.assertEqual(parsed, [{"content": "A boundary case.", "proposed_label": "restrict"}])

    def test_parse_json_object_extracts_first_object(self):
        parsed = barred_like.parse_json_object(
            'Judge notes:\n{"label":"remove","rationale":"Procedure misinformation."}\nDone.'
        )

        self.assertEqual(parsed["label"], "remove")
        self.assertEqual(parsed["rationale"], "Procedure misinformation.")

    def test_prompts_describe_diagnostic_boundary_probe_not_training_data(self):
        policy = {
            "name": "Election Integrity Period",
            "rules": {"voting_procedure": "Remove false voting time claims."},
        }

        generation_prompt = barred_like.build_generation_prompt(
            policy=policy,
            boundary_family="voting_procedure",
            num_candidates=2,
        )
        judge_prompt = barred_like.build_judge_prompt(
            policy=policy,
            candidate={"content": "Polls close at 9."},
            variant="policy_clause",
        )

        self.assertIn("diagnostic boundary probe", generation_prompt)
        self.assertIn("not synthetic training data", generation_prompt)
        self.assertIn("contrastive/boundary cases", generation_prompt)
        self.assertIn('"content"', generation_prompt)
        self.assertIn("Polls close at 9.", judge_prompt)
        self.assertIn('"label"', judge_prompt)
        self.assertIn('"policy_clause_support"', judge_prompt)
        self.assertIn('"boundary_variable_confusion"', judge_prompt)

    def test_run_barred_like_audit_generates_judges_and_summarizes(self):
        policies = {
            "election_integrity_period_v2": {
                "name": "Election Integrity Period",
                "rules": {"voting_procedure": "Remove false voting time claims."},
            }
        }
        generator = QueueClient(
            [
                json.dumps(
                    [
                        {
                            "content": "Polls close tomorrow, not today.",
                            "proposed_label": "allow",
                            "rationale": "Looks like ordinary correction.",
                            "anchor_label": "allow",
                        },
                        {
                            "content": "Maybe ballot selfies void your ballot?",
                            "proposed_label": "ambiguous",
                            "rationale": "underspecified jurisdiction and evidence.",
                        },
                    ]
                )
            ]
        )
        judges = [
            QueueClient(
                [
                    '{"label":"remove","rationale":"False voting time.","policy_clause_support":false,"boundary_variable_confusion":true}',
                    '{"label":"contextualize","rationale":"Unverified and underspecified.","policy_clause_support":false,"boundary_variable_confusion":true}',
                ]
            ),
            QueueClient(
                [
                    '{"label":"remove","rationale":"False voting time.","policy_clause_support":false,"boundary_variable_confusion":true}',
                    '{"label":"allow","rationale":"Not actionable enough.","policy_clause_support":true,"boundary_variable_confusion":true}',
                ]
            ),
        ]

        result = barred_like.run_barred_like_audit(
            policies=policies,
            families=["voting_procedure"],
            generator_client=generator,
            judge_clients=judges,
            model="fake-model",
            num_candidates=2,
            judge_variants=["policy_clause", "boundary_variable"],
        )

        self.assertEqual(result["model"], "fake-model")
        self.assertEqual(result["families"], ["voting_procedure"])
        self.assertEqual(result["num_candidates"], 2)
        self.assertEqual(result["judge_agreement_basis"], "prompt_variants")
        self.assertEqual(len(result["generated_candidates"]), 2)
        self.assertEqual(len(result["judge_results"]), 4)
        self.assertEqual(result["generated_candidates"][0]["candidate_id"], "voting_procedure-001")
        self.assertEqual(result["generated_candidates"][0]["anchor_label"], "allow")
        self.assertEqual(result["judge_results"][0]["judge_index"], 0)
        self.assertEqual(result["judge_results"][0]["judge_variant"], "policy_clause")
        self.assertEqual(result["summaries"]["voting_procedure"]["sample_count"], 2)
        self.assertEqual(result["summaries"]["voting_procedure"]["n_requested"], 2)
        self.assertEqual(result["summaries"]["voting_procedure"]["n_valid_candidates"], 2)
        self.assertEqual(result["summaries"]["voting_procedure"]["sample_yield"], 1.0)
        self.assertEqual(result["summaries"]["voting_procedure"]["judge_agreement_rate"], 0.5)
        self.assertEqual(result["summaries"]["voting_procedure"]["anchor_agreement_rate"], 0.0)
        self.assertEqual(result["summaries"]["voting_procedure"]["policy_clause_support_rate"], 0.25)
        self.assertEqual(result["summaries"]["voting_procedure"]["boundary_variable_confusion_rate"], 1.0)
        self.assertEqual(
            result["summaries"]["voting_procedure"]["label_diversity"],
            ["allow", "ambiguous", "contextualize", "remove"],
        )
        pseudo_ids = {item["candidate_id"] for item in result["pseudo_consensus_candidates"]}
        self.assertEqual(pseudo_ids, {"voting_procedure-001"})
        review_ids = {item["candidate_id"] for item in result["manual_review_candidates"]}
        self.assertEqual(review_ids, {"voting_procedure-001"})

    def test_run_barred_like_audit_records_generation_and_judge_parse_errors(self):
        policies = {
            "election_integrity_period_v2": {
                "name": "Election Integrity Period",
                "rules": {"voting_procedure": "Remove false voting time claims."},
            }
        }
        generator = QueueClient(
            [
                "not json",
                '[{"content":"Polls close tomorrow.","proposed_label":"allow","rationale":"Boundary."}]',
            ]
        )
        judges = [
            QueueClient(["not json"]),
            QueueClient(['{"label":"remove","rationale":"False voting time.","policy_clause_support":true,"boundary_variable_confusion":false}']),
        ]

        result = barred_like.run_barred_like_audit(
            policies=policies,
            families=["bad_family", "voting_procedure"],
            generator_client=generator,
            judge_clients=judges,
            model="fake-model",
            num_candidates=1,
            judge_variants=["policy_clause", "boundary_variable"],
        )

        self.assertEqual(len(result["generation_errors"]), 1)
        self.assertEqual(result["generation_errors"][0]["family"], "bad_family")
        self.assertEqual(len(result["generated_candidates"]), 1)
        self.assertEqual(len(result["judge_errors"]), 1)
        self.assertEqual(result["judge_errors"][0]["candidate_id"], "voting_procedure-001")
        self.assertEqual(result["summaries"]["bad_family"]["sample_yield"], 0.0)
        self.assertEqual(result["summaries"]["voting_procedure"]["judge_parse_error_rate"], 0.5)

    def test_cli_smoke_writes_output_with_fake_ollama_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            policies_path = tmp_dir / "policies.json"
            output_path = tmp_dir / "barred_like.json"
            policies_path.write_text(
                json.dumps(
                    {
                        "normal_civic_discussion_v1": {
                            "name": "Normal Civic Discussion",
                            "rules": {"voting_procedure": "Contextualize disputed voting discussion."},
                        },
                        "election_integrity_period_v2": {
                            "name": "Election Integrity Period",
                            "rules": {"voting_procedure": "Remove false voting time claims."},
                        }
                    }
                ),
                encoding="utf-8",
            )

            fake_client = QueueClient(
                [
                    '[{"content":"Polls close tomorrow.","proposed_label":"allow","rationale":"Boundary."}]',
                    '{"label":"remove","rationale":"False voting time.","policy_clause_support":true,"boundary_variable_confusion":false}',
                    '{"label":"remove","rationale":"False voting time.","policy_clause_support":true,"boundary_variable_confusion":false}',
                ]
            )

            with patch.object(barred_like, "OllamaClient", return_value=fake_client):
                barred_like.main(
                    [
                        "--policies",
                        str(policies_path),
                        "--families",
                        "voting_procedure",
                        "--model",
                        "fake-model",
                        "--num-candidates",
                        "1",
                        "--regime-id",
                        "election_integrity_period_v2",
                        "--judge-count",
                        "2",
                        "--output",
                        str(output_path),
                    ]
                )

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["model"], "fake-model")
            self.assertEqual(written["policy_regime_id"], "election_integrity_period_v2")
            self.assertEqual(written["judge_agreement_basis"], "prompt_variants")
            self.assertEqual([item["variant"] for item in written["judge_configs"]], ["policy_clause", "boundary_variable"])
            self.assertEqual(written["summaries"]["voting_procedure"]["sample_count"], 1)
            self.assertEqual(len(written["judge_results"]), 2)
            self.assertEqual(fake_client.calls[0]["prompt"].count("Election Integrity Period"), 1)
            self.assertNotIn("Normal Civic Discussion", fake_client.calls[0]["prompt"])

    def test_cli_rejects_too_few_judges_for_consensus(self):
        with self.assertRaises(SystemExit):
            barred_like.main(
                [
                    "--families",
                    "voting_procedure",
                    "--judge-count",
                    "1",
                ]
            )


if __name__ == "__main__":
    unittest.main()
