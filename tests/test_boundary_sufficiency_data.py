import json
from pathlib import Path
import unittest

from regime_pilot.schema import load_jsonl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "pilot" / "data"
CLARIFIED_POLICIES = DATA_DIR / "boundary_sufficiency_policies_clarified.json"
BASE_POLICIES = DATA_DIR / "policies.json"
CASES = DATA_DIR / "boundary_sufficiency_cases.jsonl"


class BoundarySufficiencyPolicyDataTests(unittest.TestCase):
    def test_clarified_policy_json_is_readable_and_ascii(self):
        raw = CLARIFIED_POLICIES.read_bytes()
        self.assertEqual(raw.decode("ascii").encode("ascii"), raw)

        policies = json.loads(raw.decode("ascii"))

        self.assertIsInstance(policies, dict)
        self.assertEqual(
            set(policies),
            {"normal_civic_discussion_v1", "election_integrity_period_v2"},
        )

    def test_clarified_policy_regime_ids_cover_boundary_cases(self):
        policies = json.loads(CLARIFIED_POLICIES.read_text(encoding="ascii"))
        cases = load_jsonl(CASES)

        case_regimes = {case["active_regime_id"] for case in cases}

        self.assertLessEqual(case_regimes, set(policies))

    def test_clarified_rules_include_four_boundary_families(self):
        policies = json.loads(CLARIFIED_POLICIES.read_text(encoding="ascii"))
        combined_rules = "\n".join(
            json.dumps(policy["rules"], sort_keys=True)
            for policy in policies.values()
        ).lower()

        expected_terms = {
            "future_reform_vs_current_voting_instruction": [
                "future reform",
                "current voting instruction",
                "current timing",
                "specific instruction",
            ],
            "obvious_satire_vs_deceptive_notice": [
                "obvious satire",
                "deceptive notice",
                "official-looking",
                "weak parody",
            ],
            "prediction_opinion_vs_false_certification": [
                "prediction opinion",
                "false certification",
                "official result",
                "active counting",
            ],
            "education_critique_quote_vs_endorsement_or_mobilization": [
                "education critique",
                "endorsement",
                "mobilization",
                "official sources",
            ],
        }

        for family, terms in expected_terms.items():
            with self.subTest(family=family):
                self.assertIn(family, combined_rules)
                for term in terms:
                    self.assertIn(term, combined_rules)

        self.assertIn("exceptions", combined_rules)
        self.assertIn("priority", combined_rules)

    def test_clarified_policy_does_not_embed_probe_posts(self):
        policy_text = CLARIFIED_POLICIES.read_text(encoding="ascii")
        cases = load_jsonl(CASES)

        for case in cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertNotIn(case["post"], policy_text)

    def test_original_policies_json_is_unmodified(self):
        policies = json.loads(BASE_POLICIES.read_text(encoding="utf-8"))

        self.assertEqual(
            policies,
            {
                "normal_civic_discussion_v1": {
                    "name": "Normal Civic Discussion",
                    "description": (
                        "Ordinary civic discussion period with broader tolerance for "
                        "political opinion, satire, and non-actionable claims."
                    ),
                    "rules": {
                        "candidate_claims": (
                            "Candidate claims may be allowed or contextualized unless "
                            "they provide actionable election misinformation."
                        ),
                        "voting_procedure": (
                            "Voting procedure claims should be reviewed when actionable, "
                            "but ordinary discussion receives broader tolerance."
                        ),
                        "satire": (
                            "Satire is generally allowed when the satirical framing is clear."
                        ),
                        "ballot_validity": (
                            "Unverified ballot validity claims should be contextualized "
                            "unless they instruct people not to vote."
                        ),
                        "counting_process": (
                            "Claims about counting process may be contextualized when "
                            "non-actionable."
                        ),
                    },
                },
                "election_integrity_period_v2": {
                    "name": "Election Integrity Period",
                    "description": (
                        "Heightened integrity period where misleading election procedure, "
                        "eligibility, ballot validity, timing, location, and counting claims "
                        "are restricted or escalated."
                    ),
                    "rules": {
                        "candidate_claims": (
                            "Misleading candidate eligibility claims near election day "
                            "should be restricted or escalated."
                        ),
                        "voting_procedure": (
                            "False or unverified voting time, location, or procedure claims "
                            "should be removed."
                        ),
                        "satire": (
                            "Satire is allowed only when clearly non-deceptive and unlikely "
                            "to mislead voters."
                        ),
                        "ballot_validity": (
                            "False ballot validity claims should be removed or escalated."
                        ),
                        "counting_process": (
                            "False counting process claims should be restricted, removed, "
                            "or escalated."
                        ),
                    },
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
