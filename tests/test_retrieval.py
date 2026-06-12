import unittest

from regime_pilot.retrieval import rank_precedents, tokenize
from regime_pilot.schema import Precedent


def make_precedent(case_id: str, regime_id: str, policy_rule: str, post: str) -> Precedent:
    return Precedent(
        case_id=case_id,
        regime_id=regime_id,
        policy_rule=policy_rule,
        post=post,
        decision="contextualize",
        rationale="rationale",
        validity_scope="scope",
        exception_tags=[],
        compatible_regimes=[regime_id],
    )


class RetrievalTests(unittest.TestCase):
    def test_tokenize_normalizes_words(self):
        self.assertEqual(
            tokenize("Polls close tomorrow, not TODAY!"),
            {"polls", "close", "tomorrow", "not", "today"},
        )

    def test_rank_precedents_prefers_policy_rule_then_text_overlap(self):
        precedents = [
            make_precedent("P1", "r1", "candidate_claims", "Candidate rumor and satire"),
            make_precedent("P2", "r1", "voting_procedure", "Polls close tomorrow not today"),
            make_precedent("P3", "r2", "voting_procedure", "Mail ballots and counting procedures"),
        ]

        ranked = rank_precedents(
            post="A viral post says polls close tomorrow, not today.",
            policy_rule="voting_procedure",
            precedents=precedents,
            top_k=2,
        )

        self.assertEqual([item.precedent.case_id for item in ranked], ["P2", "P3"])
        self.assertGreater(ranked[0].score, ranked[1].score)


if __name__ == "__main__":
    unittest.main()
