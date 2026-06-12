import json
from pathlib import Path
import unittest

from regime_pilot.schema import (
    Precedent,
    TestCase,
    load_jsonl,
    validate_precedent,
    validate_test_case,
)


class SchemaTests(unittest.TestCase):
    def test_validate_precedent_accepts_required_fields(self):
        record = {
            "case_id": "R1-P-001",
            "regime_id": "normal_civic_discussion_v1",
            "policy_rule": "candidate_claims",
            "post": "A satirical post claims Candidate A is secretly disqualified.",
            "decision": "contextualize",
            "rationale": "Satire without actionable voting misinformation.",
            "validity_scope": "Valid only under normal civic discussion.",
            "exception_tags": ["satire"],
            "compatible_regimes": ["normal_civic_discussion_v1"],
        }

        precedent = validate_precedent(record)

        self.assertIsInstance(precedent, Precedent)
        self.assertEqual(precedent.case_id, "R1-P-001")
        self.assertEqual(precedent.compatible_regimes, ["normal_civic_discussion_v1"])

    def test_validate_precedent_rejects_missing_field(self):
        record = {
            "case_id": "R1-P-001",
            "regime_id": "normal_civic_discussion_v1",
        }

        with self.assertRaisesRegex(ValueError, "policy_rule"):
            validate_precedent(record)

    def test_validate_test_case_accepts_required_fields(self):
        record = {
            "case_id": "T-001",
            "type": "cross_regime_conflict",
            "active_regime_id": "election_integrity_period_v2",
            "policy_rule": "voting_procedure",
            "post": "Polls close tomorrow, not today.",
            "expected_decision": "remove",
            "expected_rationale": "False voting time information during election integrity period.",
            "invalid_precedent_regimes": ["normal_civic_discussion_v1"],
        }

        test_case = validate_test_case(record)

        self.assertIsInstance(test_case, TestCase)
        self.assertEqual(test_case.expected_decision, "remove")

    def test_load_jsonl_reads_records(self):
        tmp_dir = Path(self.id().replace(".", "_"))
        tmp_dir.mkdir(exist_ok=True)
        path = tmp_dir / "records.jsonl"
        try:
            path.write_text(
                json.dumps({"case_id": "A"}) + "\n" + json.dumps({"case_id": "B"}) + "\n",
                encoding="utf-8",
            )

            records = load_jsonl(path)

            self.assertEqual(records, [{"case_id": "A"}, {"case_id": "B"}])
        finally:
            if path.exists():
                path.unlink()
            if tmp_dir.exists():
                tmp_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
