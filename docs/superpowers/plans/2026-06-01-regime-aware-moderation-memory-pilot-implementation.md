# Regime-aware Moderation Memory Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 鏋勫缓涓€涓彲澶嶇幇鐨?Regime-aware Moderation Memory pilot v2锛岀敤鏉ラ獙璇?precedent memory 鐨勫悓 regime utility銆佽法 regime contamination锛屼互鍙?regime-aware memory 瀵?utility-risk tradeoff 鐨勬敼鍠勩€?
**Architecture:** 绗竴鐗堜娇鐢ㄩ€忔槑 JSON/JSONL 鏁版嵁銆丳ython stdlib銆佸彲娴嬭瘯鐨?retrieval/condition/evaluation 妯″潡銆備唬鐮佹枃浠躲€佸嚱鏁板悕銆佸瓧娈靛悕淇濇寔鑻辨枃锛涙墍鏈夎惤鐩樼爺绌舵枃妗ｅ拰璁″垝鏂囨。浣跨敤涓枃銆傜涓€鐗堜笉鎺?Mem0锛屼笉渚濊禆澶栭儴 LLM API锛屽厛瀹屾垚鍙獙璇佺殑鏁版嵁缁撴瀯銆佹绱㈤€昏緫銆佹潯浠舵瀯閫犲拰鎸囨爣璁＄畻锛涘悗缁啀鎺ョ湡瀹?LLM judge/agent銆?
**Tech Stack:** Python 3, stdlib `unittest`, JSON/JSONL, stdlib `dataclasses`, `argparse`, `json`, `pathlib`, `re`, `collections`.

---

## 鏂囦欢缁撴瀯

璁″垝鍒涘缓浠ヤ笅鏂囦欢锛?
- `pilot/data/policies.json`锛氫袱涓?moderation regimes 鐨?policy 瀹氫箟銆?- `pilot/data/precedents.jsonl`锛歝onstruction precedents锛屾瘡琛屼竴鏉?precedent record銆?- `pilot/data/test_cases.jsonl`锛氭祴璇曟牱鏈紝姣忚涓€鏉?test case銆?- `pilot/src/regime_pilot/__init__.py`锛氬寘鍒濆鍖栥€?- `pilot/src/regime_pilot/schema.py`锛氭暟鎹被銆丣SONL 璇诲彇銆佸瓧娈垫牎楠屻€?- `pilot/src/regime_pilot/retrieval.py`锛氶€忔槑 lexical retrieval baseline銆?- `pilot/src/regime_pilot/conditions.py`锛歚policy_only`銆乣naive_memory`銆乣regime_filtered`銆乣regime_aware` 鍥涚鏉′欢鐨?memory selection銆?- `pilot/src/regime_pilot/evaluate.py`锛歳etrieval-side 鍜?label-side 鎸囨爣銆?- `pilot/src/regime_pilot/run_pilot.py`锛氬懡浠よ鍏ュ彛锛岃鍙栨暟鎹苟杈撳嚭缁撴灉 JSON銆?- `pilot/results/.gitkeep`锛氫繚鐣欑粨鏋滅洰褰曘€?- `tests/test_schema.py`锛歴chema 鍜?JSONL 鏍￠獙娴嬭瘯銆?- `tests/test_retrieval.py`锛氭绱㈣涓烘祴璇曘€?- `tests/test_conditions.py`锛氬洓绉嶆潯浠剁殑 memory selection 娴嬭瘯銆?- `tests/test_evaluate.py`锛氭寚鏍囪绠楁祴璇曘€?
涓嶄慨鏀癸細

- `iclr2025_conference.tex`锛氬厛涓嶅姩璁烘枃姝ｆ枃锛岀瓑 pilot 璺戝嚭绗竴寮犺〃鍚庡啀閲嶅啓銆?- `claudecode.result`锛氫綔涓烘棫瀹為獙璁板綍淇濈暀銆?
## 鎵ц鍘熷垯

- 鏂囨。涓枃锛屼唬鐮佽嫳鏂囥€?- 浠ｇ爜璧?TDD锛氬厛鍐?failing test锛屽啀鍐欐渶灏忓疄鐜般€?- 绗竴鐗堝彧鍋氶€忔槑銆佸彲妫€鏌ョ殑 pilot锛屼笉寮曞叆 Mem0 鎴栧鏉備緷璧栥€?- 姣忎竴姝ラ兘瑕佽兘鍗曠嫭杩愯娴嬭瘯銆?- 濡傛灉 `git` 鍙敤锛屾瘡涓换鍔＄粨鏉熷悗鎻愪氦锛涘綋鍓?Windows 鐜涓?`git` 涓嶅湪 PATH锛屽洜姝ゆ墽琛屾椂鑻ヤ粛涓嶅彲鐢紝搴旇褰曗€滄湭鎻愪氦鍘熷洜鈥濓紝涓嶈闃诲瀹炵幇銆?
---

### Task 1: Schema 涓?JSONL 璇诲彇

**Files:**

- Create: `pilot/src/regime_pilot/__init__.py`
- Create: `pilot/src/regime_pilot/schema.py`
- Create: `tests/test_schema.py`

- [ ] **Step 1: 鍐?failing tests**

鍒涘缓 `tests/test_schema.py`锛?
```python
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


def test_validate_precedent_accepts_required_fields():
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

    assert isinstance(precedent, Precedent)
    assert precedent.case_id == "R1-P-001"
    assert precedent.compatible_regimes == ["normal_civic_discussion_v1"]


def test_validate_precedent_rejects_missing_field():
    record = {
        "case_id": "R1-P-001",
        "regime_id": "normal_civic_discussion_v1",
    }

    with self.assertRaisesRegex(ValueError, "policy_rule"):
        validate_precedent(record)


def test_validate_test_case_accepts_required_fields():
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

    assert isinstance(test_case, TestCase)
    assert test_case.expected_decision == "remove"


def test_load_jsonl_reads_records(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text(
        json.dumps({"case_id": "A"}) + "\n" + json.dumps({"case_id": "B"}) + "\n",
        encoding="utf-8",
    )

    records = load_jsonl(path)

    assert records == [{"case_id": "A"}, {"case_id": "B"}]
```

- [ ] **Step 2: 杩愯娴嬭瘯纭澶辫触**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_schema -v
```

Expected: FAIL锛屽洜涓?`regime_pilot.schema` 灏氫笉瀛樺湪銆?
- [ ] **Step 3: 鍐欐渶灏忓疄鐜?*

鍒涘缓 `pilot/src/regime_pilot/__init__.py`锛?
```python
"""Regime-aware moderation memory pilot."""
```

鍒涘缓 `pilot/src/regime_pilot/schema.py`锛?
```python
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
```

- [ ] **Step 4: 杩愯娴嬭瘯纭閫氳繃**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_schema -v
```

Expected: PASS銆?
---

### Task 2: 閫忔槑 lexical retrieval baseline

**Files:**

- Create: `pilot/src/regime_pilot/retrieval.py`
- Create: `tests/test_retrieval.py`

- [ ] **Step 1: 鍐?failing tests**

鍒涘缓 `tests/test_retrieval.py`锛?
```python
from regime_pilot.retrieval import rank_precedents, tokenize
from regime_pilot.schema import Precedent


def make_precedent(case_id, regime_id, policy_rule, post):
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


def test_tokenize_normalizes_words():
    assert tokenize("Polls close tomorrow, not TODAY!") == {"polls", "close", "tomorrow", "not", "today"}


def test_rank_precedents_prefers_policy_rule_then_text_overlap():
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

    assert [item.precedent.case_id for item in ranked] == ["P2", "P3"]
    assert ranked[0].score > ranked[1].score
```

- [ ] **Step 2: 杩愯娴嬭瘯纭澶辫触**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_retrieval -v
```

Expected: FAIL锛屽洜涓?`regime_pilot.retrieval` 灏氫笉瀛樺湪銆?
- [ ] **Step 3: 鍐欐渶灏忓疄鐜?*

鍒涘缓 `pilot/src/regime_pilot/retrieval.py`锛?
```python
from __future__ import annotations

from dataclasses import dataclass
import re

from regime_pilot.schema import Precedent


TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RetrievalResult:
    precedent: Precedent
    score: float


def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def score_precedent(post: str, policy_rule: str, precedent: Precedent) -> float:
    query_tokens = tokenize(post)
    precedent_tokens = tokenize(precedent.post)
    if not query_tokens or not precedent_tokens:
        text_score = 0.0
    else:
        text_score = len(query_tokens & precedent_tokens) / len(query_tokens | precedent_tokens)
    rule_bonus = 1.0 if precedent.policy_rule == policy_rule else 0.0
    return rule_bonus + text_score


def rank_precedents(
    post: str,
    policy_rule: str,
    precedents: list[Precedent],
    top_k: int,
) -> list[RetrievalResult]:
    ranked = [
        RetrievalResult(precedent=precedent, score=score_precedent(post, policy_rule, precedent))
        for precedent in precedents
    ]
    ranked.sort(key=lambda item: (-item.score, item.precedent.case_id))
    return ranked[:top_k]
```

- [ ] **Step 4: 杩愯娴嬭瘯纭閫氳繃**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_retrieval -v
```

Expected: PASS銆?
---

### Task 3: 鍥涚瀹為獙鏉′欢鐨?memory selection

**Files:**

- Create: `pilot/src/regime_pilot/conditions.py`
- Create: `tests/test_conditions.py`

- [ ] **Step 1: 鍐?failing tests**

鍒涘缓 `tests/test_conditions.py`锛?
```python
from regime_pilot.conditions import select_memories
from regime_pilot.schema import Precedent, TestCase


def precedent(case_id, regime_id, compatible_regimes):
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


def test_case():
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


def test_policy_only_selects_no_memories():
    selected = select_memories("policy_only", test_case(), [], top_k=3)

    assert selected == []


def test_naive_memory_can_select_invalid_old_regime():
    memories = [
        precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
        precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
    ]

    selected = select_memories("naive_memory", test_case(), memories, top_k=2)

    assert [item.precedent.case_id for item in selected] == ["R1-P-001", "R2-P-001"]


def test_regime_filtered_keeps_only_active_regime():
    memories = [
        precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
        precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
    ]

    selected = select_memories("regime_filtered", test_case(), memories, top_k=3)

    assert [item.precedent.case_id for item in selected] == ["R2-P-001"]


def test_regime_aware_keeps_active_and_compatible_memories():
    memories = [
        precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]),
        precedent("I-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1", "election_integrity_period_v2"]),
        precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]),
    ]

    selected = select_memories("regime_aware", test_case(), memories, top_k=3)

    assert [item.precedent.case_id for item in selected] == ["I-P-001", "R2-P-001"]
```

- [ ] **Step 2: 杩愯娴嬭瘯纭澶辫触**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_conditions -v
```

Expected: FAIL锛屽洜涓?`conditions.py` 灏氫笉瀛樺湪銆?
- [ ] **Step 3: 鍐欐渶灏忓疄鐜?*

鍒涘缓 `pilot/src/regime_pilot/conditions.py`锛?
```python
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
```

- [ ] **Step 4: 杩愯娴嬭瘯纭閫氳繃**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_conditions -v
```

Expected: PASS銆?
---

### Task 4: 鎸囨爣璁＄畻

**Files:**

- Create: `pilot/src/regime_pilot/evaluate.py`
- Create: `tests/test_evaluate.py`

- [ ] **Step 1: 鍐?failing tests**

鍒涘缓 `tests/test_evaluate.py`锛?
```python
from regime_pilot.evaluate import evaluate_retrieval, summarize_metrics
from regime_pilot.retrieval import RetrievalResult
from regime_pilot.schema import Precedent, TestCase


def precedent(case_id, regime_id, compatible_regimes):
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


def test_case():
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


def test_evaluate_retrieval_counts_invalid_activation():
    selected = [
        RetrievalResult(precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]), 1.2),
        RetrievalResult(precedent("R2-P-001", "election_integrity_period_v2", ["election_integrity_period_v2"]), 1.1),
    ]

    result = evaluate_retrieval(test_case(), selected)

    assert result["retrieved_count"] == 2
    assert result["invalid_activation_count"] == 1
    assert result["invalid_activation_rate"] == 0.5


def test_summarize_metrics_averages_rates():
    summary = summarize_metrics([
        {"invalid_activation_rate": 0.5, "retrieved_count": 2},
        {"invalid_activation_rate": 0.0, "retrieved_count": 1},
    ])

    assert summary["n"] == 2
    assert summary["mean_invalid_activation_rate"] == 0.25
    assert summary["mean_retrieved_count"] == 1.5
```

- [ ] **Step 2: 杩愯娴嬭瘯纭澶辫触**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_evaluate -v
```

Expected: FAIL锛屽洜涓?`evaluate.py` 灏氫笉瀛樺湪銆?
- [ ] **Step 3: 鍐欐渶灏忓疄鐜?*

鍒涘缓 `pilot/src/regime_pilot/evaluate.py`锛?
```python
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
        if item.precedent.regime_id in test_case.invalid_precedent_regimes
        or test_case.active_regime_id not in item.precedent.compatible_regimes
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
```

- [ ] **Step 4: 杩愯娴嬭瘯纭閫氳繃**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_evaluate -v
```

Expected: PASS銆?
---

### Task 5: 绗竴鐗?seed 鏁版嵁

**Files:**

- Create: `pilot/data/policies.json`
- Create: `pilot/data/precedents.jsonl`
- Create: `pilot/data/test_cases.jsonl`
- Create: `pilot/results/.gitkeep`

- [ ] **Step 1: 鍒涘缓鏁版嵁鏂囦欢**

鍒涘缓 `pilot/data/policies.json`锛屽寘鍚袱涓?regimes锛?
```json
{
  "normal_civic_discussion_v1": {
    "name": "Normal Civic Discussion",
    "description": "Ordinary civic discussion period with broader tolerance for political opinion, satire, and non-actionable claims.",
    "rules": {
      "candidate_claims": "Candidate claims may be allowed or contextualized unless they provide actionable election misinformation.",
      "voting_procedure": "Voting procedure claims should be reviewed when actionable, but ordinary discussion receives broader tolerance.",
      "satire": "Satire is generally allowed when the satirical framing is clear.",
      "ballot_validity": "Unverified ballot validity claims should be contextualized unless they instruct people not to vote.",
      "counting_process": "Claims about counting process may be contextualized when non-actionable."
    }
  },
  "election_integrity_period_v2": {
    "name": "Election Integrity Period",
    "description": "Heightened integrity period where misleading election procedure, eligibility, ballot validity, timing, location, and counting claims are restricted or escalated.",
    "rules": {
      "candidate_claims": "Misleading candidate eligibility claims near election day should be restricted or escalated.",
      "voting_procedure": "False or unverified voting time, location, or procedure claims should be removed.",
      "satire": "Satire is allowed only when clearly non-deceptive and unlikely to mislead voters.",
      "ballot_validity": "False ballot validity claims should be removed or escalated.",
      "counting_process": "False counting process claims should be restricted, removed, or escalated."
    }
  }
}
```

鍒涘缓 `pilot/data/precedents.jsonl`锛岃嚦灏?10 鏉℃牱渚嬶紝瑕嗙洊 R1/R2 鍜?5 绫?policy_rule銆?
鍒涘缓 `pilot/data/test_cases.jsonl`锛岃嚦灏?10 鏉℃牱渚嬶紝瑕嗙洊涓夌 test case type銆?
鍒涘缓 `pilot/results/.gitkeep`銆?
- [ ] **Step 2: 鐢?schema 娴嬭瘯璇诲彇鏁版嵁**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -c "from regime_pilot.schema import load_jsonl, validate_precedent, validate_test_case; [validate_precedent(r) for r in load_jsonl('pilot/data/precedents.jsonl')]; [validate_test_case(r) for r in load_jsonl('pilot/data/test_cases.jsonl')]; print('data ok')"
```

Expected:

```text
data ok
```

---

### Task 6: 鍛戒护琛?runner

**Files:**

- Create: `pilot/src/regime_pilot/run_pilot.py`
- Create: `tests/test_run_pilot.py`

- [ ] **Step 1: 鍐?failing test**

鍒涘缓 `tests/test_run_pilot.py`锛?
```python
import json
from pathlib import Path

from regime_pilot.run_pilot import run_pilot


def test_run_pilot_returns_condition_summaries(tmp_path):
    policies_path = tmp_path / "policies.json"
    precedents_path = tmp_path / "precedents.jsonl"
    test_cases_path = tmp_path / "test_cases.jsonl"

    policies_path.write_text("{}", encoding="utf-8")
    precedents_path.write_text(
        json.dumps({
            "case_id": "R1-P-001",
            "regime_id": "normal_civic_discussion_v1",
            "policy_rule": "voting_procedure",
            "post": "Polls close tomorrow not today.",
            "decision": "contextualize",
            "rationale": "Normal period contextualization.",
            "validity_scope": "Normal civic discussion only.",
            "exception_tags": [],
            "compatible_regimes": ["normal_civic_discussion_v1"]
        }) + "\n",
        encoding="utf-8",
    )
    test_cases_path.write_text(
        json.dumps({
            "case_id": "T-001",
            "type": "cross_regime_conflict",
            "active_regime_id": "election_integrity_period_v2",
            "policy_rule": "voting_procedure",
            "post": "Polls close tomorrow not today.",
            "expected_decision": "remove",
            "expected_rationale": "False voting time.",
            "invalid_precedent_regimes": ["normal_civic_discussion_v1"]
        }) + "\n",
        encoding="utf-8",
    )

    result = run_pilot(
        policies_path=policies_path,
        precedents_path=precedents_path,
        test_cases_path=test_cases_path,
        top_k=3,
    )

    assert "naive_memory" in result["summaries"]
    assert result["summaries"]["naive_memory"]["mean_invalid_activation_rate"] == 1.0
    assert result["summaries"]["policy_only"]["mean_invalid_activation_rate"] == 0.0
```

- [ ] **Step 2: 杩愯娴嬭瘯纭澶辫触**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_run_pilot -v
```

Expected: FAIL锛屽洜涓?`run_pilot.py` 灏氫笉瀛樺湪銆?
- [ ] **Step 3: 鍐欐渶灏忓疄鐜?*

鍒涘缓 `pilot/src/regime_pilot/run_pilot.py`锛?
```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from regime_pilot.conditions import CONDITIONS, select_memories
from regime_pilot.evaluate import evaluate_retrieval, summarize_metrics
from regime_pilot.schema import (
    load_jsonl,
    validate_precedent,
    validate_test_case,
)


def run_pilot(
    policies_path: str | Path,
    precedents_path: str | Path,
    test_cases_path: str | Path,
    top_k: int,
) -> dict[str, Any]:
    Path(policies_path).read_text(encoding="utf-8")
    precedents = [validate_precedent(record) for record in load_jsonl(precedents_path)]
    test_cases = [validate_test_case(record) for record in load_jsonl(test_cases_path)]

    rows_by_condition: dict[str, list[dict[str, Any]]] = {}
    for condition in sorted(CONDITIONS):
        rows = []
        for test_case in test_cases:
            selected = select_memories(condition, test_case, precedents, top_k)
            row = evaluate_retrieval(test_case, selected)
            row["condition"] = condition
            rows.append(row)
        rows_by_condition[condition] = rows

    return {
        "top_k": top_k,
        "rows": rows_by_condition,
        "summaries": {
            condition: summarize_metrics(rows)
            for condition, rows in rows_by_condition.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", default="pilot/data/policies.json")
    parser.add_argument("--precedents", default="pilot/data/precedents.jsonl")
    parser.add_argument("--test-cases", default="pilot/data/test_cases.jsonl")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--output", default="pilot/results/retrieval_metrics.json")
    args = parser.parse_args()

    result = run_pilot(
        policies_path=args.policies,
        precedents_path=args.precedents,
        test_cases_path=args.test_cases,
        top_k=args.top_k,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 杩愯娴嬭瘯纭閫氳繃**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_run_pilot -v
```

Expected: PASS銆?
- [ ] **Step 5: 杩愯鏁翠釜 pilot**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m regime_pilot.run_pilot --output pilot/results/retrieval_metrics.json
```

Expected:

```text
wrote pilot/results/retrieval_metrics.json
```

---

### Task 7: 鏈€缁堥獙璇佷笌鐮旂┒璁板綍

**Files:**

- Create: `docs/research_notes/2026-06-01-pilot-implementation-status.md`
- Modify: `docs/research_notes/2026-06-01-artifact-index.md`

- [ ] **Step 1: 杩愯鍏ㄩ噺娴嬭瘯**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest discover -s tests -v
```

Expected: 鎵€鏈夋祴璇?PASS銆?
- [ ] **Step 2: 杩愯 pilot**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m regime_pilot.run_pilot --output pilot/results/retrieval_metrics.json
```

Expected: 鐢熸垚 `pilot/results/retrieval_metrics.json`銆?
- [ ] **Step 3: 鍐欎腑鏂囩姸鎬佽褰?*

鍒涘缓 `docs/research_notes/2026-06-01-pilot-implementation-status.md`锛岃褰曪細

- 宸插垱寤虹殑鏁版嵁鍜屼唬鐮佹枃浠讹紱
- 杩愯杩囩殑娴嬭瘯鍛戒护锛?- pilot 杈撳嚭鏂囦欢锛?- 褰撳墠缁撴灉鍙槸 retrieval-side 鎸囨爣锛屼笉鏄畬鏁?LLM agent 缁撴灉锛?- 涓嬩竴姝ユ槸鎺ュ叆鐪熷疄 LLM agent/judge锛岃绠?policy adherence銆乻tale rationale 鍜?contamination銆?
- [ ] **Step 4: 鏇存柊 artifact index**

鍦?`docs/research_notes/2026-06-01-artifact-index.md` 涓姞鍏ワ細

- implementation plan 璺緞锛?- pilot 鏁版嵁璺緞锛?- pilot 浠ｇ爜璺緞锛?- pilot 缁撴灉璺緞锛?- implementation status 璺緞銆?
- [ ] **Step 5: 濡傛灉 git 鍙敤鍒欐彁浜?*

Run:

```powershell
git status --short
git add docs pilot tests
git commit -m "feat: add regime-aware moderation memory pilot scaffold"
```

Expected: commit 鎴愬姛銆傝嫢 `git` 涓嶅彲鐢紝璁板綍鍛戒护澶辫触鍘熷洜锛屼笉瑕佹妸瀹炵幇瑙嗕负澶辫触銆?
