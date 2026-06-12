import unittest

from regime_pilot.conditions import select_memories
from regime_pilot.schema import Precedent, TestCase


def precedent(case_id: str, regime_id: str, compatible_regimes: list[str]) -> Precedent:
    return Precedent(
        case_id=case_id,
        regime_id=regime_id,
        policy_rule="voting_procedure",
        post="Polls close tomorrow not today",
        decision="contextualize",
        rationale="rationale",
        validity_scope="scope",
        exception_tags=[],
        compatible_regimes=compatible_regimes,
    )


def make_test_case() -> TestCase:
    return TestCase(
        case_id="T1",
        type="cross_regime_conflict",
        active_regime_id="election_integrity_period_v2",
        policy_rule="voting_procedure",
        post="A post says polls close tomorrow, not today.",
        expected_decision="remove",
        expected_rationale="False voting time information.",
        invalid_precedent_regimes=["normal_civic_discussion_v1"],
    )


class ConditionTests(unittest.TestCase):
    def test_policy_only_selects_no_memories(self):
        selected = select_memories("policy_only", make_test_case(), [], top_k=3)

        self.assertEqual(selected, [])

    def test_naive_memory_can_select_invalid_old_regime(self):
        memories = [
            precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
            precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
        ]

        selected = select_memories("naive_memory", make_test_case(), memories, top_k=2)

        self.assertEqual([item.precedent.case_id for item in selected], ["R1-P-001", "R2-P-001"])

    def test_regime_filtered_keeps_only_active_regime(self):
        memories = [
            precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
            precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
        ]

        selected = select_memories("regime_filtered", make_test_case(), memories, top_k=3)

        self.assertEqual([item.precedent.case_id for item in selected], ["R2-P-001"])

    def test_regime_aware_keeps_active_and_compatible_memories(self):
        memories = [
            precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
            precedent(
                "I-P-001",
                "normal_civic_discussion_v1",
                ["normal_civic_discussion_v1", "election_integrity_period_v2"],
            ),
            precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
        ]

        selected = select_memories("regime_aware", make_test_case(), memories, top_k=3)

        self.assertEqual([item.precedent.case_id for item in selected], ["I-P-001", "R2-P-001"])


if __name__ == "__main__":
    unittest.main()
