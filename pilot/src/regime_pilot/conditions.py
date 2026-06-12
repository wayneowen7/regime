from __future__ import annotations

from regime_pilot.retrieval import RetrievalResult, rank_precedents
from regime_pilot.schema import Precedent, TestCase


CONDITIONS = {
    "policy_only",
    "naive_memory",
    "regime_filtered",
    "regime_aware",
}


def _ensure_condition(condition: str) -> None:
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")


def select_memories(
    condition: str,
    test_case: TestCase,
    precedents: list[Precedent],
    top_k: int,
) -> list[RetrievalResult]:
    _ensure_condition(condition)
    if condition == "policy_only":
        return []
    if condition == "regime_filtered":
        eligible = [
            precedent
            for precedent in precedents
            if precedent.regime_id == test_case.active_regime_id
        ]
    elif condition == "regime_aware":
        eligible = [
            precedent
            for precedent in precedents
            if test_case.active_regime_id in precedent.compatible_regimes
        ]
    else:
        eligible = precedents

    return rank_precedents(
        post=test_case.post,
        policy_rule=test_case.policy_rule,
        precedents=eligible,
        top_k=top_k,
    )
