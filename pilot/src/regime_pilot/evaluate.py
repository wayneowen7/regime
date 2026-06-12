from __future__ import annotations

from typing import Any

from regime_pilot.retrieval import RetrievalResult
from regime_pilot.schema import TestCase


def evaluate_retrieval(
    test_case: TestCase,
    selected: list[RetrievalResult],
) -> dict[str, Any]:
    invalid = [
        item
        for item in selected
        if test_case.active_regime_id not in item.precedent.compatible_regimes
    ]
    retrieved_count = len(selected)
    invalid_count = len(invalid)
    invalid_rate = invalid_count / retrieved_count if retrieved_count else 0.0
    return {
        "case_id": test_case.case_id,
        "type": test_case.type,
        "active_regime_id": test_case.active_regime_id,
        "retrieved_count": retrieved_count,
        "invalid_activation_count": invalid_count,
        "invalid_activation_rate": invalid_rate,
        "retrieved_case_ids": [item.precedent.case_id for item in selected],
        "invalid_case_ids": [item.precedent.case_id for item in invalid],
    }


def summarize_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "n": 0,
            "mean_invalid_activation_rate": 0.0,
            "mean_retrieved_count": 0.0,
        }
    return {
        "n": len(rows),
        "mean_invalid_activation_rate": sum(row["invalid_activation_rate"] for row in rows) / len(rows),
        "mean_retrieved_count": sum(row["retrieved_count"] for row in rows) / len(rows),
    }
