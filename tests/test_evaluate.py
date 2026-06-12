import unittest

from regime_pilot.evaluate import evaluate_retrieval, summarize_metrics
from regime_pilot.retrieval import RetrievalResult
from regime_pilot.schema import Precedent, TestCase


def precedent(case_id: str, regime_id: str, compatible_regimes: list[str]) -> Precedent:
    return Precedent(
        case_id=case_id,
        regime_id=regime_id,
        policy_rule="voting_procedure",
        post="Polls close tomorrow",
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
        post="Polls close tomorrow",
        expected_decision="remove",
        expected_rationale="False voting time.",
        invalid_precedent_regimes=["normal_civic_discussion_v1"],
    )


class EvaluateTests(unittest.TestCase):
    def test_evaluate_retrieval_counts_invalid_activation(self):
        selected = [
            RetrievalResult(
                precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
                1.2,
            ),
            RetrievalResult(
                precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
                1.1,
            ),
        ]

        result = evaluate_retrieval(make_test_case(), selected)

        self.assertEqual(result["retrieved_count"], 2)
        self.assertEqual(result["invalid_activation_count"], 1)
        self.assertEqual(result["invalid_activation_rate"], 0.5)

    def test_summarize_metrics_averages_rates(self):
        summary = summarize_metrics(
            [
                {"invalid_activation_rate": 0.5, "retrieved_count": 2},
                {"invalid_activation_rate": 0.0, "retrieved_count": 1},
            ]
        )

        self.assertEqual(summary["n"], 2)
        self.assertEqual(summary["mean_invalid_activation_rate"], 0.25)
        self.assertEqual(summary["mean_retrieved_count"], 1.5)

    def test_evaluate_retrieval_treats_compatible_cross_regime_memory_as_valid(self):
        selected = [
            RetrievalResult(
                precedent(
                    "R1-P-VALID",
                    "normal_civic_discussion_v1",
                    ["normal_civic_discussion_v1", "election_integrity_period_v2"],
                ),
                1.2,
            )
        ]

        result = evaluate_retrieval(make_test_case(), selected)

        self.assertEqual(result["invalid_activation_count"], 0)
        self.assertEqual(result["invalid_activation_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
