from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


DECISIONS = {"allow", "contextualize", "restrict", "remove", "escalate"}
TEST_CASE_TYPES = {
    "within_regime_holdout",
    "cross_regime_conflict",
    "boundary_ambiguity",
}


@dataclass(frozen=True)
class Precedent:
    case_id: str
    regime_id: str
    policy_rule: str
    post: str
    decision: str
    rationale: str
    validity_scope: str
    exception_tags: list[str]
    compatible_regimes: list[str]


@dataclass(frozen=True)
class TestCase:
    case_id: str
    type: str
    active_regime_id: str
    policy_rule: str
    post: str
    expected_decision: str
    expected_rationale: str
    invalid_precedent_regimes: list[str]


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} invalid JSON: {exc}") from exc
    return records


def _require(record: dict[str, Any], field: str) -> Any:
    if field not in record:
        raise ValueError(f"Missing required field: {field}")
    return record[field]


def _require_list(record: dict[str, Any], field: str) -> list[str]:
    value = _require(record, field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Field must be a list of strings: {field}")
    return value


def _require_decision(record: dict[str, Any], field: str) -> str:
    value = str(_require(record, field))
    if value not in DECISIONS:
        raise ValueError(f"Invalid decision for {field}: {value}")
    return value


def validate_precedent(record: dict[str, Any]) -> Precedent:
    return Precedent(
        case_id=str(_require(record, "case_id")),
        regime_id=str(_require(record, "regime_id")),
        policy_rule=str(_require(record, "policy_rule")),
        post=str(_require(record, "post")),
        decision=_require_decision(record, "decision"),
        rationale=str(_require(record, "rationale")),
        validity_scope=str(_require(record, "validity_scope")),
        exception_tags=_require_list(record, "exception_tags"),
        compatible_regimes=_require_list(record, "compatible_regimes"),
    )


def validate_test_case(record: dict[str, Any]) -> TestCase:
    case_type = str(_require(record, "type"))
    if case_type not in TEST_CASE_TYPES:
        raise ValueError(f"Invalid test case type: {case_type}")
    return TestCase(
        case_id=str(_require(record, "case_id")),
        type=case_type,
        active_regime_id=str(_require(record, "active_regime_id")),
        policy_rule=str(_require(record, "policy_rule")),
        post=str(_require(record, "post")),
        expected_decision=_require_decision(record, "expected_decision"),
        expected_rationale=str(_require(record, "expected_rationale")),
        invalid_precedent_regimes=_require_list(record, "invalid_precedent_regimes"),
    )
