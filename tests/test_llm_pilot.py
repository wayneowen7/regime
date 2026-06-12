import unittest

from regime_pilot.llm_pilot import (
    build_agent_prompt,
    decision_family,
    evaluate_agent_output,
    parse_agent_output,
)
from regime_pilot.retrieval import RetrievalResult
from regime_pilot.schema import Precedent, TestCase


def make_precedent(case_id: str, regime_id: str, compatible_regimes: list[str]) -> Precedent:
    return Precedent(
        case_id=case_id,
        regime_id=regime_id,
        policy_rule="voting_procedure",
        post="Polls close tomorrow, not today.",
        decision="contextualize",
        rationale="Normal-period discussion receives context.",
        validity_scope="Normal civic discussion only.",
        exception_tags=["hearsay"],
        compatible_regimes=compatible_regimes,
    )


def make_test_case() -> TestCase:
    return TestCase(
        case_id="T-001",
        type="cross_regime_conflict",
        active_regime_id="election_integrity_period_v2",
        policy_rule="voting_procedure",
        post="A post says polls close tomorrow, not today.",
        expected_decision="remove",
        expected_rationale="False voting time information.",
        invalid_precedent_regimes=["normal_civic_discussion_v1"],
    )


class LlmPilotTests(unittest.TestCase):
    def test_decision_family_groups_adjacent_actions(self):
        self.assertEqual(decision_family("allow"), "non_removal")
        self.assertEqual(decision_family("contextualize"), "non_removal")
        self.assertEqual(decision_family("restrict"), "intervention")
        self.assertEqual(decision_family("remove"), "intervention")
        self.assertEqual(decision_family("escalate"), "intervention")
        self.assertEqual(decision_family("parse_error"), "unknown")

    def test_build_agent_prompt_contains_policy_case_and_precedents(self):
        prompt = build_agent_prompt(
            policy={
                "name": "Election Integrity Period",
                "description": "Heightened election integrity policy.",
                "rules": {"voting_procedure": "Remove false voting time claims."},
            },
            test_case=make_test_case(),
            selected=[
                RetrievalResult(
                    make_precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
                    1.2,
                )
            ],
        )

        self.assertIn("Election Integrity Period", prompt)
        self.assertIn("A post says polls close tomorrow", prompt)
        self.assertIn("R1-P-001", prompt)
        self.assertNotIn("R2-P-001", prompt)
        self.assertIn('"decision"', prompt)
        self.assertIn("Do not include the current content case_id", prompt)

    def test_build_agent_prompt_operational_view_hides_precedent_metadata(self):
        prompt = build_agent_prompt(
            policy={
                "name": "Election Integrity Period",
                "description": "Heightened election integrity policy.",
                "rules": {"voting_procedure": "Remove false voting time claims."},
            },
            test_case=make_test_case(),
            selected=[
                RetrievalResult(
                    make_precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
                    1.2345,
                )
            ],
            memory_view="operational",
        )

        self.assertIn("case_id: R1-P-001", prompt)
        self.assertIn("post: Polls close tomorrow, not today.", prompt)
        self.assertIn("decision: contextualize", prompt)
        self.assertIn("rationale: Normal-period discussion receives context.", prompt)
        self.assertNotIn("regime_id: normal_civic_discussion_v1", prompt)
        self.assertNotIn("validity_scope:", prompt)
        self.assertNotIn("compatible_regimes:", prompt)
        self.assertNotIn("retrieval_score:", prompt)

    def test_build_agent_prompt_brief_policy_without_stale_warning(self):
        prompt = build_agent_prompt(
            policy={
                "name": "Election Integrity Period",
                "description": "Heightened election integrity policy.",
                "rules": {"voting_procedure": "Remove false voting time claims."},
            },
            test_case=make_test_case(),
            selected=[],
            memory_view="operational",
            policy_view="brief",
            stale_warning=False,
        )

        self.assertIn("active_policy_focus: voting_procedure", prompt)
        self.assertNotIn("Policy rules:", prompt)
        self.assertNotIn("Remove false voting time claims.", prompt)
        self.assertNotIn("may be stale", prompt)
        self.assertNotIn("rationale still fits", prompt)

    def test_build_agent_prompt_formats_nested_policy_rules_readably(self):
        prompt = build_agent_prompt(
            policy={
                "name": "Clarified Election Integrity Period",
                "description": "Policy with structured boundary clarifications.",
                "rules": {
                    "voting_procedure": {
                        "remove": ["False current voting time claims."],
                        "allow": ["Non-actionable future reform discussion."],
                    }
                },
            },
            test_case=make_test_case(),
            selected=[],
            policy_view="full",
        )

        self.assertIn('"remove": ["False current voting time claims."]', prompt)
        self.assertIn('"allow": ["Non-actionable future reform discussion."]', prompt)
        self.assertNotIn("'remove'", prompt)

    def test_parse_agent_output_extracts_json_from_fenced_response(self):
        output = parse_agent_output(
            """Here is the decision:
```json
{"decision":"remove","rationale":"False voting time.","used_precedents":["R2-P-001"]}
```"""
        )

        self.assertEqual(output["decision"], "remove")
        self.assertEqual(output["used_precedents"], ["R2-P-001"])

    def test_parse_agent_output_handles_invalid_json(self):
        output = parse_agent_output("I would remove it.")

        self.assertEqual(output["decision"], "parse_error")
        self.assertIn("raw_response", output)

    def test_evaluate_agent_output_counts_policy_adherence_and_invalid_used_precedents(self):
        selected = [
            RetrievalResult(
                make_precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
                1.2,
            ),
            RetrievalResult(
                make_precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
                1.1,
            ),
        ]
        result = evaluate_agent_output(
            test_case=make_test_case(),
            selected=selected,
            output={
                "decision": "remove",
                "rationale": "False voting time.",
                "used_precedents": ["R1-P-001", "R2-P-001"],
            },
        )

        self.assertTrue(result["policy_adherence"])
        self.assertTrue(result["decision_family_adherence"])
        self.assertEqual(result["invalid_used_precedent_count"], 1)
        self.assertEqual(result["invalid_used_precedent_ids"], ["R1-P-001"])

    def test_evaluate_agent_output_counts_family_adherence_for_nearby_labels(self):
        result = evaluate_agent_output(
            test_case=make_test_case(),
            selected=[],
            output={
                "decision": "restrict",
                "rationale": "Misleading voting procedure.",
                "used_precedents": [],
            },
        )

        self.assertFalse(result["policy_adherence"])
        self.assertTrue(result["decision_family_adherence"])

    def test_evaluate_agent_output_records_unknown_used_precedents(self):
        result = evaluate_agent_output(
            test_case=make_test_case(),
            selected=[],
            output={
                "decision": "remove",
                "rationale": "False voting time.",
                "used_precedents": ["T-001"],
            },
        )

        self.assertEqual(result["unknown_used_precedent_ids"], ["T-001"])

    def test_evaluate_agent_output_detects_stale_rationale_without_explicit_use(self):
        result = evaluate_agent_output(
            test_case=make_test_case(),
            selected=[
                RetrievalResult(
                    make_precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
                    1.2,
                )
            ],
            output={
                "decision": "contextualize",
                "rationale": "Normal-period discussion receives context.",
                "used_precedents": [],
            },
        )

        self.assertEqual(result["stale_rationale_match_count"], 1)
        self.assertEqual(result["stale_rationale_precedent_ids"], ["R1-P-001"])


if __name__ == "__main__":
    unittest.main()
