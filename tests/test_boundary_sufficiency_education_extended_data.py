from pathlib import Path
import unittest

from regime_pilot.schema import load_jsonl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "pilot" / "data"

BASE_CASES = DATA_DIR / "boundary_sufficiency_cases.jsonl"
EXTENDED_CASES = DATA_DIR / "boundary_sufficiency_cases_education_extended.jsonl"
CURRENT_GUIDANCE = DATA_DIR / "boundary_sufficiency_guidance_current_education_extended.jsonl"
STALE_GUIDANCE = DATA_DIR / "boundary_sufficiency_guidance_stale_education_extended.jsonl"

EDUCATION_FAMILY = "education_critique_quote_vs_endorsement_or_mobilization"
VALID_DECISIONS = {"allow", "contextualize", "remove"}
NORMAL_REGIME = "normal_civic_discussion_v1"
INTEGRITY_REGIME = "election_integrity_period_v2"


class BoundarySufficiencyEducationExtendedDataTests(unittest.TestCase):
    def test_extended_cases_include_original_twelve_and_four_new_probes(self):
        base_cases = load_jsonl(BASE_CASES)
        extended_cases = load_jsonl(EXTENDED_CASES)

        self.assertEqual(len(base_cases), 12)
        self.assertEqual(len(extended_cases), 16)
        self.assertEqual(extended_cases[:12], base_cases)
        self.assertEqual(
            [case["case_id"] for case in extended_cases[12:]],
            ["BS-T-013", "BS-T-014", "BS-T-015", "BS-T-016"],
        )

    def test_extended_cases_have_unique_ids_and_valid_decisions(self):
        cases = load_jsonl(EXTENDED_CASES)
        case_ids = [case["case_id"] for case in cases]

        self.assertEqual(len(case_ids), len(set(case_ids)))

        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertIn(case["expected_decision"], VALID_DECISIONS)

    def test_new_education_probes_have_required_family_metadata(self):
        cases = {
            case["case_id"]: case
            for case in load_jsonl(EXTENDED_CASES)
            if case["case_id"] in {"BS-T-013", "BS-T-014", "BS-T-015", "BS-T-016"}
        }

        self.assertEqual(set(cases), {"BS-T-013", "BS-T-014", "BS-T-015", "BS-T-016"})

        expected_labels = {
            "BS-T-013": "quote_for_debunking",
            "BS-T-014": "quote_for_critique",
            "BS-T-015": "quote_plus_endorsement",
            "BS-T-016": "quote_plus_mobilization",
        }

        for case_id, expected_label in expected_labels.items():
            with self.subTest(case_id=case_id):
                rationale = cases[case_id]["expected_rationale"]
                self.assertIn(f"boundary_family={EDUCATION_FAMILY}", rationale)
                self.assertIn(f"hidden_anchor_label={expected_label}", rationale)
                self.assertIn("anchor_rationale=", rationale)

    def test_guidance_files_have_unique_ids_and_valid_decisions(self):
        for path in [CURRENT_GUIDANCE, STALE_GUIDANCE]:
            with self.subTest(path=path.name):
                guidance = load_jsonl(path)
                guidance_ids = [item["case_id"] for item in guidance]

                self.assertEqual(len(guidance), 16)
                self.assertEqual(len(guidance_ids), len(set(guidance_ids)))

                for item in guidance:
                    self.assertIn(item["decision"], VALID_DECISIONS)

    def test_new_current_guidance_compatible_regimes_follow_decision_direction(self):
        guidance = {
            item["case_id"]: item
            for item in load_jsonl(CURRENT_GUIDANCE)
            if item["case_id"] in {"BS-C-013", "BS-C-014", "BS-C-015", "BS-C-016"}
        }

        self.assertEqual(
            set(guidance),
            {"BS-C-013", "BS-C-014", "BS-C-015", "BS-C-016"},
        )
        self.assertEqual(guidance["BS-C-013"]["decision"], "contextualize")
        self.assertEqual(guidance["BS-C-014"]["decision"], "allow")
        self.assertEqual(guidance["BS-C-015"]["decision"], "remove")
        self.assertEqual(guidance["BS-C-016"]["decision"], "remove")

        for case_id in ["BS-C-013", "BS-C-014"]:
            with self.subTest(case_id=case_id):
                self.assertEqual(
                    set(guidance[case_id]["compatible_regimes"]),
                    {NORMAL_REGIME, INTEGRITY_REGIME},
                )

        for case_id in ["BS-C-015", "BS-C-016"]:
            with self.subTest(case_id=case_id):
                self.assertEqual(
                    guidance[case_id]["compatible_regimes"],
                    [INTEGRITY_REGIME],
                )

    def test_new_stale_guidance_compatible_regimes_are_intentionally_narrow(self):
        guidance = {
            item["case_id"]: item
            for item in load_jsonl(STALE_GUIDANCE)
            if item["case_id"] in {"BS-S-013", "BS-S-014", "BS-S-015", "BS-S-016"}
        }

        self.assertEqual(
            set(guidance),
            {"BS-S-013", "BS-S-014", "BS-S-015", "BS-S-016"},
        )

        self.assertEqual(guidance["BS-S-013"]["compatible_regimes"], [INTEGRITY_REGIME])
        for case_id in ["BS-S-014", "BS-S-015", "BS-S-016"]:
            with self.subTest(case_id=case_id):
                self.assertEqual(guidance[case_id]["compatible_regimes"], [NORMAL_REGIME])

        self.assertIn("stale for quote for debunking", guidance["BS-S-013"]["validity_scope"])
        self.assertIn("stale for quote plus endorsement", guidance["BS-S-014"]["validity_scope"])
        self.assertIn("stale for quote plus endorsement", guidance["BS-S-015"]["validity_scope"])
        self.assertIn("stale for quote plus mobilization", guidance["BS-S-016"]["validity_scope"])


if __name__ == "__main__":
    unittest.main()
