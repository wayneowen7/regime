from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from regime_pilot.schema import DECISIONS, load_jsonl


ACTION_ORDER = ["allow", "contextualize", "restrict", "remove", "escalate"]


@dataclass(frozen=True)
class ActionRule:
    action: str
    criterion: str


@dataclass(frozen=True)
class OperationalRule:
    rule_id: str
    standard: str
    boundary_rule: str
    boundary_variables: list[str]
    action_rules: list[ActionRule]

    @property
    def has_action_rubric(self) -> bool:
        return bool(self.action_rules)


@dataclass(frozen=True)
class PolicyIR:
    policy_id: str
    name: str
    description: str
    rules: dict[str, OperationalRule]


@dataclass(frozen=True)
class CompiledPolicy:
    prompt: str
    sidecar: dict[str, Any]


@dataclass(frozen=True)
class BoundaryActionContrastSet:
    boundary_family: str
    action_contrast: str
    case_ids: list[str]
    expected_actions: list[str]
    boundary_variables: list[str]

    @property
    def key(self) -> str:
        return f"{self.boundary_family}::{self.action_contrast}"


def _metadata_from_rationale(rationale: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for part in rationale.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        stripped_key = key.strip()
        stripped_value = value.strip()
        if stripped_key:
            metadata[stripped_key] = stripped_value
    return metadata


def _parse_action_rubric(items: list[Any]) -> list[ActionRule]:
    parsed: list[ActionRule] = []
    for item in items:
        text = str(item).strip()
        if ":" not in text:
            continue
        action, criterion = text.split(":", 1)
        normalized_action = action.strip().lower()
        if normalized_action not in DECISIONS:
            continue
        parsed.append(ActionRule(action=normalized_action, criterion=criterion.strip()))

    order = {action: index for index, action in enumerate(ACTION_ORDER)}
    return sorted(parsed, key=lambda rule: order.get(rule.action, len(order)))


def _build_operational_rule(rule_id: str, raw_rule: Any) -> OperationalRule:
    if isinstance(raw_rule, str):
        return OperationalRule(
            rule_id=rule_id,
            standard=raw_rule,
            boundary_rule="",
            boundary_variables=[],
            action_rules=[],
        )
    if not isinstance(raw_rule, dict):
        raw_rule = {"standard": str(raw_rule)}

    boundary_variables = raw_rule.get("boundary_variables", [])
    if not isinstance(boundary_variables, list):
        boundary_variables = []

    action_rubric = raw_rule.get("action_rubric", [])
    if not isinstance(action_rubric, list):
        action_rubric = []

    return OperationalRule(
        rule_id=rule_id,
        standard=str(raw_rule.get("standard", "")),
        boundary_rule=str(raw_rule.get("boundary_rule", "")),
        boundary_variables=[str(item) for item in boundary_variables],
        action_rules=_parse_action_rubric(action_rubric),
    )


def build_policy_ir(policy_id: str, policy: dict[str, Any]) -> PolicyIR:
    rules = {
        str(rule_id): _build_operational_rule(str(rule_id), raw_rule)
        for rule_id, raw_rule in policy.get("rules", {}).items()
    }
    return PolicyIR(
        policy_id=policy_id,
        name=str(policy.get("name", policy_id)),
        description=str(policy.get("description", "")),
        rules=rules,
    )


def _format_rule_prompt(rule: OperationalRule) -> list[str]:
    lines = [f"Rule: {rule.rule_id}"]
    if rule.standard:
        lines.append(f"Standard: {rule.standard}")
    if rule.boundary_rule:
        lines.append(f"Boundary: {rule.boundary_rule}")
    if rule.boundary_variables:
        lines.append("Boundary variables: " + ", ".join(rule.boundary_variables))
    if rule.action_rules:
        lines.append("Action rubric:")
        for action_rule in rule.action_rules:
            lines.append(f"- {action_rule.action}: {action_rule.criterion}")
    return lines


def _format_runner_rule_text(
    rule: OperationalRule,
    action_edge_cues: dict[str, list[str]] | None = None,
) -> str:
    lines = []
    if rule.standard:
        lines.append(f"Standard: {rule.standard}")
    if rule.boundary_rule:
        lines.append(f"Boundary: {rule.boundary_rule}")
    if rule.boundary_variables:
        lines.append("Boundary variables: " + ", ".join(rule.boundary_variables))
    if action_edge_cues:
        cue_lines = []
        for action in ACTION_ORDER:
            variables = action_edge_cues.get(action, [])
            if variables:
                cue_lines.append(f"- {action} cues: {', '.join(variables)}")
        if cue_lines:
            lines.append("Action-edge cues:")
            lines.extend(cue_lines)
    if rule.action_rules:
        lines.append("Action rubric:")
        for action_rule in rule.action_rules:
            lines.append(f"- {action_rule.action}: {action_rule.criterion}")
    return "\n".join(lines)


def compile_compact_policy(ir: PolicyIR, target_rule: str | None = None) -> CompiledPolicy:
    selected_rules = (
        {target_rule: ir.rules[target_rule]}
        if target_rule is not None
        else ir.rules
    )
    if not selected_rules:
        raise ValueError("Cannot compile a policy with no rules")

    action_list = ", ".join(action for action in ACTION_ORDER if action in DECISIONS)
    lines = [
        "Operational moderation policy.",
        f"Policy: {ir.name}",
        f"Regime: {ir.policy_id}",
        f"Scope: {ir.description}",
        f"Actions: {action_list}",
        "",
    ]
    for rule in selected_rules.values():
        lines.extend(_format_rule_prompt(rule))
        lines.append("")
    lines.extend(
        [
            "When rules conflict, apply the most specific boundary and the stricter action threshold.",
            "When the policy does not specify enough information for a reliable action, use escalate.",
            'Return JSON only: {"decision":"allow","rationale":"short reason","used_precedents":[]}',
        ]
    )

    sidecar = {
        "artifact_type": "polar_compact_policy",
        "policy_id": ir.policy_id,
        "target_rule": target_rule,
        "included_rules": list(selected_rules),
        "rule_summaries": {
            rule_id: {
                "has_boundary_rule": bool(rule.boundary_rule),
                "boundary_variable_count": len(rule.boundary_variables),
                "action_rule_count": len(rule.action_rules),
            }
            for rule_id, rule in selected_rules.items()
        },
    }
    return CompiledPolicy(prompt="\n".join(lines).strip(), sidecar=sidecar)


def _case_hint_index(cases: list[dict[str, Any]] | None) -> dict[str, dict[str, dict[str, Any]]]:
    if not cases:
        return {}

    severity = {action: index for index, action in enumerate(ACTION_ORDER)}
    sorted_cases = sorted(
        cases,
        key=lambda case: severity.get(str(case.get("expected_decision", "")), -1),
        reverse=True,
    )
    hints: dict[str, dict[str, dict[str, Any]]] = {}
    for case in sorted_cases:
        policy_id = str(case.get("active_regime_id", ""))
        rule_id = str(case.get("policy_rule", ""))
        if not policy_id or not rule_id:
            continue
        rule_hints = hints.setdefault(policy_id, {}).setdefault(
            rule_id,
            {"case_ids": [], "action_edge_cues": {}},
        )
        case_id = str(case.get("case_id", ""))
        if case_id and case_id not in rule_hints["case_ids"]:
            rule_hints["case_ids"].append(case_id)

        metadata = _metadata_from_rationale(str(case.get("expected_rationale", "")))
        expected_decision = str(case.get("expected_decision", ""))
        if expected_decision not in DECISIONS:
            continue
        action_cues = rule_hints["action_edge_cues"].setdefault(expected_decision, [])
        for variable in metadata.get("boundary_variables", "").split("|"):
            stripped = variable.strip()
            if stripped and stripped not in action_cues:
                action_cues.append(stripped)
    return hints


def _trim_action_edge_cues(
    action_edge_cues: dict[str, list[str]],
    limit_per_action: int = 8,
) -> dict[str, list[str]]:
    return {
        action: variables[:limit_per_action]
        for action, variables in action_edge_cues.items()
        if variables
    }


def compile_policy_collection(
    policies: dict[str, Any],
    cases: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    compiled_policies: dict[str, Any] = {}
    sidecars: list[dict[str, Any]] = []
    case_hints = _case_hint_index(cases)
    for policy_id, policy in policies.items():
        ir = build_policy_ir(str(policy_id), policy)
        compiled_rules: dict[str, str] = {}
        for rule_id in ir.rules:
            compiled = compile_compact_policy(ir, target_rule=rule_id)
            hints = case_hints.get(str(policy_id), {}).get(rule_id, {})
            action_edge_cues = _trim_action_edge_cues(
                {
                    str(action): [str(item) for item in variables]
                    for action, variables in hints.get("action_edge_cues", {}).items()
                }
            )
            compiled_rules[rule_id] = _format_runner_rule_text(
                ir.rules[rule_id],
                action_edge_cues=action_edge_cues,
            )
            sidecar = dict(compiled.sidecar)
            sidecar["case_ids"] = list(hints.get("case_ids", []))
            sidecar["action_edge_cues"] = action_edge_cues
            sidecars.append(sidecar)
        compiled_policies[str(policy_id)] = {
            "name": f"POLAR-Compact {ir.name}",
            "description": ir.description,
            "rules": compiled_rules,
        }
    return compiled_policies, sidecars


def build_boundary_action_contrast_sets(
    cases: list[dict[str, Any]],
) -> list[BoundaryActionContrastSet]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for case in cases:
        metadata = _metadata_from_rationale(str(case.get("expected_rationale", "")))
        boundary_family = metadata.get("boundary_family", "unknown")
        action_contrast = metadata.get("action_contrast", "unknown")
        key = (boundary_family, action_contrast)
        group = grouped.setdefault(
            key,
            {
                "case_ids": [],
                "expected_actions": [],
                "boundary_variables": [],
            },
        )
        case_id = str(case.get("case_id", ""))
        if case_id and case_id not in group["case_ids"]:
            group["case_ids"].append(case_id)
        expected_decision = str(case.get("expected_decision", ""))
        if expected_decision in DECISIONS and expected_decision not in group["expected_actions"]:
            group["expected_actions"].append(expected_decision)
        variables = metadata.get("boundary_variables", "")
        for variable in variables.split("|"):
            stripped = variable.strip()
            if stripped and stripped not in group["boundary_variables"]:
                group["boundary_variables"].append(stripped)

    order = {action: index for index, action in enumerate(ACTION_ORDER)}
    contrast_sets = []
    for (boundary_family, action_contrast), group in sorted(grouped.items()):
        contrast_sets.append(
            BoundaryActionContrastSet(
                boundary_family=boundary_family,
                action_contrast=action_contrast,
                case_ids=group["case_ids"],
                expected_actions=sorted(
                    group["expected_actions"],
                    key=lambda action: order.get(action, len(order)),
                ),
                boundary_variables=group["boundary_variables"],
            )
        )
    return contrast_sets


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile structured moderation policies into POLAR-Compact prompts.",
    )
    parser.add_argument("--policies", required=True, help="Input policy JSON file.")
    parser.add_argument("--output-policies", required=True, help="Output compiled policy JSON file.")
    parser.add_argument("--output-sidecar", required=True, help="Output compiler sidecar JSON file.")
    parser.add_argument("--cases", help="Optional JSONL cases to summarize contrast sets.")
    parser.add_argument("--output-contrast-sets", help="Optional output JSON for contrast sets.")
    args = parser.parse_args(argv)

    policies = json.loads(Path(args.policies).read_text(encoding="utf-8"))
    cases = load_jsonl(args.cases) if args.cases else None
    compiled_policies, sidecars = compile_policy_collection(policies, cases=cases)
    _write_json(Path(args.output_policies), compiled_policies)
    _write_json(Path(args.output_sidecar), {"sidecars": sidecars})

    if cases and args.output_contrast_sets:
        contrast_sets = build_boundary_action_contrast_sets(cases)
        _write_json(
            Path(args.output_contrast_sets),
            {"contrast_sets": [item.__dict__ | {"key": item.key} for item in contrast_sets]},
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
