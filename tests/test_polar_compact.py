from pathlib import Path
import unittest

from regime_pilot.polar_compact import (
    build_boundary_action_contrast_sets,
    build_policy_ir,
    compile_policy_collection,
    compile_compact_policy,
)
from regime_pilot.schema import load_jsonl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "pilot" / "data"

ACTION_POLICIES = DATA_DIR / "action_granularity_policies_action_rubric.json"
ACTION_CASES = DATA_DIR / "action_granularity_cases.jsonl"


class PolarCompactTests(unittest.TestCase):
    def test_build_policy_ir_preserves_boundary_and_action_layers(self):
        policies = __import__("json").loads(ACTION_POLICIES.read_text(encoding="utf-8"))
        ir = build_policy_ir("election_integrity_period_v2", policies["election_integrity_period_v2"])

        self.assertEqual(ir.policy_id, "election_integrity_period_v2")
        self.assertIn("ballot_validity", ir.rules)
        ballot_rule = ir.rules["ballot_validity"]

        self.assertIn("Debunking and critique", ballot_rule.boundary_rule)
        self.assertEqual(
            [rule.action for rule in ballot_rule.action_rules],
            ["allow", "contextualize", "remove", "escalate"],
        )
        self.assertTrue(ballot_rule.has_action_rubric)

    def test_compile_compact_policy_outputs_prompt_without_sidecar_evidence(self):
        policies = __import__("json").loads(ACTION_POLICIES.read_text(encoding="utf-8"))
        ir = build_policy_ir("election_integrity_period_v2", policies["election_integrity_period_v2"])

        compiled = compile_compact_policy(ir, target_rule="ballot_validity")

        self.assertIn("Operational moderation policy", compiled.prompt)
        self.assertIn("Actions:", compiled.prompt)
        self.assertIn("Boundary:", compiled.prompt)
        self.assertIn("Action rubric:", compiled.prompt)
        self.assertIn("Return JSON only", compiled.prompt)
        self.assertNotIn("supporting_probes", compiled.prompt)
        self.assertNotIn("evidence_trace", compiled.prompt)
        self.assertLessEqual(len(compiled.prompt), 1800)
        self.assertEqual(compiled.sidecar["policy_id"], "election_integrity_period_v2")
        self.assertEqual(compiled.sidecar["target_rule"], "ballot_validity")
        self.assertEqual(compiled.sidecar["artifact_type"], "polar_compact_policy")

    def test_boundary_action_contrast_sets_group_existing_cases_by_family_and_edge(self):
        cases = load_jsonl(ACTION_CASES)

        contrast_sets = build_boundary_action_contrast_sets(cases)

        keys = {(item.boundary_family, item.action_contrast) for item in contrast_sets}
        self.assertIn(
            (
                "education_critique_quote_vs_endorsement_or_mobilization",
                "allow_vs_contextualize",
            ),
            keys,
        )
        self.assertIn(
            (
                "education_critique_quote_vs_endorsement_or_mobilization",
                "remove_vs_escalate",
            ),
            keys,
        )
        for contrast_set in contrast_sets:
            with self.subTest(key=contrast_set.key):
                self.assertGreaterEqual(len(contrast_set.case_ids), 1)
                self.assertEqual(len(contrast_set.case_ids), len(set(contrast_set.case_ids)))
                self.assertNotEqual(contrast_set.expected_actions, [])

    def test_compile_policy_collection_uses_runner_friendly_compact_rule_text(self):
        policies = __import__("json").loads(ACTION_POLICIES.read_text(encoding="utf-8"))

        compiled_policies, sidecars = compile_policy_collection(policies)

        self.assertEqual(len(sidecars), 6)
        original_lengths = []
        compiled_lengths = []
        for policy_id, policy in policies.items():
            for rule_id, raw_rule in policy["rules"].items():
                original_lengths.append(
                    len(__import__("json").dumps(raw_rule, ensure_ascii=True, sort_keys=True))
                )
                compiled_rule = compiled_policies[policy_id]["rules"][rule_id]
                compiled_lengths.append(len(compiled_rule))
                self.assertIn("Boundary:", compiled_rule)
                self.assertIn("Action rubric:", compiled_rule)
                self.assertNotIn("Operational moderation policy.", compiled_rule)
                self.assertNotIn("Return JSON only", compiled_rule)

        self.assertLessEqual(
            sum(compiled_lengths) / len(compiled_lengths),
            sum(original_lengths) / len(original_lengths),
        )

    def test_compile_policy_collection_preserves_action_edge_cues_from_cases(self):
        policies = __import__("json").loads(ACTION_POLICIES.read_text(encoding="utf-8"))
        cases = load_jsonl(ACTION_CASES)

        compiled_policies, sidecars = compile_policy_collection(policies, cases=cases)

        satire_rule = compiled_policies["election_integrity_period_v2"]["rules"]["satire"]
        self.assertIn("Action-edge cues:", satire_rule)
        self.assertIn(
            "remove cues: official_looking_format, real_precinct, current_cancellation, weak_parody_label, high_confusion_risk",
            satire_rule,
        )
        self.assertIn(
            "escalate cues: official_looking_format, real_precincts, current_closure, coordinated_distribution, voters_should_go_home",
            satire_rule,
        )
        self.assertNotIn("Critical variables:", satire_rule)
        self.assertIn("case_ids", sidecars[0])
        self.assertIn("action_edge_cues", sidecars[0])

        original_lengths = []
        compiled_lengths = []
        for policy_id, policy in policies.items():
            for rule_id, raw_rule in policy["rules"].items():
                original_lengths.append(
                    len(__import__("json").dumps(raw_rule, ensure_ascii=True, sort_keys=True))
                )
                compiled_lengths.append(len(compiled_policies[policy_id]["rules"][rule_id]))

        self.assertLessEqual(
            sum(compiled_lengths) / len(compiled_lengths),
            (sum(original_lengths) / len(original_lengths)) * 1.5,
        )


if __name__ == "__main__":
    unittest.main()
