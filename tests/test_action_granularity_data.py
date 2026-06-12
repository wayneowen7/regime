from pathlib import Path
import unittest

from regime_pilot.schema import load_jsonl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "pilot" / "data"

ACTION_CASES = DATA_DIR / "action_granularity_cases.jsonl"
BOUNDARY_GUIDANCE = DATA_DIR / "action_granularity_guidance_boundary.jsonl"
ACTION_GUIDANCE = DATA_DIR / "action_granularity_guidance_action.jsonl"
ABSTRACT_POLICIES = DATA_DIR / "action_granularity_policies_abstract.json"
BOUNDARY_POLICIES = DATA_DIR / "action_granularity_policies_boundary_clarified.json"
ACTION_POLICIES = DATA_DIR / "action_granularity_policies_action_rubric.json"

VALID_DECISIONS = {"allow", "contextualize", "restrict", "remove", "escalate"}
EXPECTED_CASE_IDS = {f"AG-T-{index:03d}" for index in range(1, 13)}
EXPECTED_BOUNDARY_IDS = {f"AG-B-{index:03d}" for index in range(1, 13)}
EXPECTED_ACTION_IDS = {f"AG-A-{index:03d}" for index in range(1, 13)}


class ActionGranularityDataTests(unittest.TestCase):
    def test_action_cases_have_expected_size_unique_ids_and_valid_decisions(self):
        cases = load_jsonl(ACTION_CASES)
        case_ids = [case["case_id"] for case in cases]

        self.assertEqual(set(case_ids), EXPECTED_CASE_IDS)
        self.assertEqual(len(case_ids), len(set(case_ids)))

        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(case["type"], "boundary_ambiguity")
                self.assertIn(case["expected_decision"], VALID_DECISIONS)
                self.assertIn("boundary_family=", case["expected_rationale"])
                self.assertIn("hidden_anchor_label=", case["expected_rationale"])
                self.assertIn("decision_family=", case["expected_rationale"])
                self.assertIn("action_contrast=", case["expected_rationale"])
                self.assertIn("boundary_variables=", case["expected_rationale"])

    def test_cases_cover_action_contrasts_and_decision_families(self):
        cases = load_jsonl(ACTION_CASES)
        rationales = "\n".join(case["expected_rationale"] for case in cases)

        for contrast in [
            "allow_vs_contextualize",
            "remove_vs_escalate",
            "contextualize_vs_remove",
        ]:
            self.assertIn(f"action_contrast={contrast}", rationales)

        self.assertIn("decision_family=non_removal", rationales)
        self.assertIn("decision_family=intervention", rationales)

    def test_guidance_files_match_cases_and_add_action_rubric_layer(self):
        boundary_guidance = load_jsonl(BOUNDARY_GUIDANCE)
        action_guidance = load_jsonl(ACTION_GUIDANCE)

        self.assertEqual({item["case_id"] for item in boundary_guidance}, EXPECTED_BOUNDARY_IDS)
        self.assertEqual({item["case_id"] for item in action_guidance}, EXPECTED_ACTION_IDS)
        self.assertEqual(len(boundary_guidance), len(action_guidance))

        boundary_decisions = {item["decision"] for item in boundary_guidance}
        action_decisions = {item["decision"] for item in action_guidance}
        self.assertTrue(boundary_decisions <= VALID_DECISIONS)
        self.assertTrue(action_decisions <= VALID_DECISIONS)

        action_rationales = "\n".join(item["rationale"] for item in action_guidance)
        self.assertIn("action rubric", action_rationales.lower())
        self.assertIn("allow vs contextualize", action_rationales.lower())
        self.assertIn("remove vs escalate", action_rationales.lower())

    def test_policy_views_exist_for_abstract_boundary_and_action_conditions(self):
        self.assertTrue(ABSTRACT_POLICIES.exists())
        self.assertTrue(BOUNDARY_POLICIES.exists())
        self.assertTrue(ACTION_POLICIES.exists())


if __name__ == "__main__":
    unittest.main()
