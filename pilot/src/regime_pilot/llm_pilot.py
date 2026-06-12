from __future__ import annotations

import json
from typing import Any

from regime_pilot.retrieval import RetrievalResult
from regime_pilot.schema import DECISIONS, TestCase


DECISION_FAMILIES = {
    "allow": "non_removal",
    "contextualize": "non_removal",
    "restrict": "intervention",
    "remove": "intervention",
    "escalate": "intervention",
}
MEMORY_VIEWS = {"transparent", "operational"}
POLICY_VIEWS = {"full", "brief"}
RATIONALE_STOPWORDS = {
    "a",
    "about",
    "and",
    "are",
    "as",
    "can",
    "does",
    "for",
    "is",
    "it",
    "not",
    "of",
    "or",
    "rather",
    "that",
    "the",
    "their",
    "this",
    "to",
    "when",
    "with",
}


def decision_family(decision: str) -> str:
    return DECISION_FAMILIES.get(decision, "unknown")


def _format_rule_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _format_rules(rules: dict[str, Any]) -> str:
    return "\n".join(
        f"- {name}: {_format_rule_value(text)}" for name, text in sorted(rules.items())
    )


def _format_policy_section(
    policy: dict[str, Any],
    test_case: TestCase,
    memory_view: str,
    policy_view: str,
) -> str:
    if policy_view not in POLICY_VIEWS:
        raise ValueError(f"Unknown policy_view: {policy_view}")
    regime_id_line = (
        f"regime_id: {test_case.active_regime_id}\n"
        if memory_view == "transparent"
        else ""
    )
    header = (
        "Current policy regime:\n"
        f"name: {policy.get('name', test_case.active_regime_id)}\n"
        f"{regime_id_line}"
        f"description: {policy.get('description', '')}\n"
    )
    if policy_view == "brief":
        return header + f"active_policy_focus: {test_case.policy_rule}"
    return header + f"\nPolicy rules:\n{_format_rules(policy.get('rules', {}))}"


def _format_precedent(result: RetrievalResult) -> str:
    precedent = result.precedent
    return (
        f"case_id: {precedent.case_id}\n"
        f"regime_id: {precedent.regime_id}\n"
        f"policy_rule: {precedent.policy_rule}\n"
        f"post: {precedent.post}\n"
        f"decision: {precedent.decision}\n"
        f"rationale: {precedent.rationale}\n"
        f"validity_scope: {precedent.validity_scope}\n"
        f"compatible_regimes: {', '.join(precedent.compatible_regimes)}\n"
        f"retrieval_score: {result.score:.4f}"
    )


def _format_operational_precedent(result: RetrievalResult) -> str:
    precedent = result.precedent
    return (
        f"case_id: {precedent.case_id}\n"
        f"post: {precedent.post}\n"
        f"decision: {precedent.decision}\n"
        f"rationale: {precedent.rationale}"
    )


def _format_precedents(selected: list[RetrievalResult], memory_view: str) -> str:
    if memory_view not in MEMORY_VIEWS:
        raise ValueError(f"Unknown memory_view: {memory_view}")
    formatter = _format_operational_precedent if memory_view == "operational" else _format_precedent
    memories = "\n\n".join(formatter(item) for item in selected)
    if not memories:
        return "No historical precedents were retrieved."
    return memories


def build_agent_prompt(
    policy: dict[str, Any],
    test_case: TestCase,
    selected: list[RetrievalResult],
    memory_view: str = "transparent",
    policy_view: str = "full",
    stale_warning: bool = True,
) -> str:
    memories = _format_precedents(selected, memory_view)
    decisions = ", ".join(sorted(DECISIONS))
    policy_section = _format_policy_section(policy, test_case, memory_view, policy_view)
    if memory_view == "operational":
        if stale_warning:
            precedent_instruction = (
                "- Retrieved precedents are historical operational examples and may be stale.\n"
                "- Apply the current policy regime first; use a precedent only if its rationale still fits the current policy."
            )
        else:
            precedent_instruction = "- Retrieved precedents are historical operational examples."
    else:
        precedent_instruction = (
            "- Use precedents only when they are compatible with the current regime."
        )
    return f"""You are a content moderation agent.

{policy_section}

Content to moderate:
case_id: {test_case.case_id}
policy_rule: {test_case.policy_rule}
post: {test_case.post}

Retrieved historical precedents:
{memories}

Instructions:
- Apply the current policy regime first.
{precedent_instruction}
- Return JSON only.
- The "decision" value must be one of: {decisions}.
- "used_precedents" must be a list of precedent case_id strings that influenced the decision.
- Do not include the current content case_id in "used_precedents"; only use IDs from retrieved historical precedents.

Required JSON schema:
{{"decision":"remove","rationale":"short reason","used_precedents":[]}}
"""


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No JSON object found")


def parse_agent_output(text: str) -> dict[str, Any]:
    try:
        parsed = _extract_json_object(text)
    except ValueError:
        return {
            "decision": "parse_error",
            "rationale": "",
            "used_precedents": [],
            "raw_response": text,
        }

    decision = str(parsed.get("decision", "parse_error"))
    if decision not in DECISIONS:
        decision = "parse_error"
    used_precedents = parsed.get("used_precedents", [])
    if not isinstance(used_precedents, list):
        used_precedents = []
    used_precedents = [str(item) for item in used_precedents]
    return {
        "decision": decision,
        "rationale": str(parsed.get("rationale", "")),
        "used_precedents": used_precedents,
        "raw_response": text,
    }


def _rationale_tokens(text: str) -> set[str]:
    raw_tokens = []
    current = []
    for char in text.lower():
        if char.isalnum() or char == "-":
            current.append(char)
        elif current:
            raw_tokens.append("".join(current))
            current = []
    if current:
        raw_tokens.append("".join(current))
    return {
        token
        for token in raw_tokens
        if len(token) >= 3 and token not in RATIONALE_STOPWORDS
    }


def _stale_rationale_matches(
    test_case: TestCase,
    selected: list[RetrievalResult],
    rationale: str,
) -> list[str]:
    output_tokens = _rationale_tokens(rationale)
    if not output_tokens:
        return []
    matches = []
    for item in selected:
        precedent = item.precedent
        if test_case.active_regime_id in precedent.compatible_regimes:
            continue
        precedent_tokens = _rationale_tokens(precedent.rationale)
        if len(output_tokens & precedent_tokens) >= 3:
            matches.append(precedent.case_id)
    return matches


def evaluate_agent_output(
    test_case: TestCase,
    selected: list[RetrievalResult],
    output: dict[str, Any],
) -> dict[str, Any]:
    selected_by_id = {item.precedent.case_id: item for item in selected}
    invalid_used = []
    unknown_used = []
    for case_id in output.get("used_precedents", []):
        item = selected_by_id.get(case_id)
        if item is None:
            unknown_used.append(case_id)
            continue
        if test_case.active_regime_id not in item.precedent.compatible_regimes:
            invalid_used.append(case_id)

    expected_family = decision_family(test_case.expected_decision)
    model_family = decision_family(str(output.get("decision", "parse_error")))
    stale_rationale_matches = _stale_rationale_matches(
        test_case,
        selected,
        str(output.get("rationale", "")),
    )
    return {
        "case_id": test_case.case_id,
        "type": test_case.type,
        "active_regime_id": test_case.active_regime_id,
        "expected_decision": test_case.expected_decision,
        "model_decision": output.get("decision", "parse_error"),
        "expected_decision_family": expected_family,
        "model_decision_family": model_family,
        "policy_adherence": output.get("decision") == test_case.expected_decision,
        "decision_family_adherence": model_family == expected_family,
        "used_precedents": output.get("used_precedents", []),
        "invalid_used_precedent_count": len(invalid_used),
        "invalid_used_precedent_ids": invalid_used,
        "unknown_used_precedent_count": len(unknown_used),
        "unknown_used_precedent_ids": unknown_used,
        "stale_rationale_match_count": len(stale_rationale_matches),
        "stale_rationale_precedent_ids": stale_rationale_matches,
        "rationale": output.get("rationale", ""),
    }
