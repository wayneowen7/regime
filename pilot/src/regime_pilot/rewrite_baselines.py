from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MODES = ("template", "length_matched")
FORBIDDEN_PATTERNS = (
    re.compile(r"AG-T-\d+", re.IGNORECASE),
    re.compile(r"\bcase_ids?\b", re.IGNORECASE),
    re.compile(r"\bcontrast_sets?\b", re.IGNORECASE),
)


def _rule_json_length(rule: Any) -> int:
    return len(json.dumps(rule, ensure_ascii=True, sort_keys=True))


def _average_rule_chars(policies: dict[str, Any]) -> float:
    lengths = [
        _rule_json_length(rule)
        for policy in policies.values()
        for rule in policy.get("rules", {}).values()
    ]
    if not lengths:
        return 0.0
    return sum(lengths) / len(lengths)


def _sanitize_text(text: str) -> str:
    sanitized = text
    for pattern in FORBIDDEN_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized.strip()


def _source_rule_text(raw_rule: Any) -> str:
    if isinstance(raw_rule, str):
        return _sanitize_text(raw_rule)
    if isinstance(raw_rule, dict):
        parts = []
        for key in ("standard", "description", "rule", "boundary_rule"):
            value = raw_rule.get(key)
            if value:
                parts.append(str(value))
        if not parts:
            parts.append(json.dumps(raw_rule, ensure_ascii=True, sort_keys=True))
        return _sanitize_text(" ".join(parts))
    return _sanitize_text(str(raw_rule))


def _template_rewrite_rule(rule_id: str, raw_rule: Any) -> str:
    source_text = _source_rule_text(raw_rule)
    lines = [
        f"Operational rewrite: apply the {rule_id} rule using the current policy text only.",
        f"Source standard: {source_text}",
        (
            "Decision guidance: identify the claim, separate critique or education from "
            "endorsement, assess current operational risk, and choose the least severe "
            "action that addresses the risk."
        ),
        (
            "When the policy leaves an action boundary unresolved, escalate rather than "
            "inventing facts outside the policy."
        ),
    ]
    return _sanitize_text("\n".join(lines))


def _target_rule_length(
    target_policies: dict[str, Any],
    policy_id: str,
    rule_id: str,
    fallback: int,
) -> int:
    target_policy = target_policies.get(policy_id, {})
    target_rules = target_policy.get("rules", {}) if isinstance(target_policy, dict) else {}
    if rule_id not in target_rules:
        return fallback
    return _rule_json_length(target_rules[rule_id])


def _fit_to_length(text: str, target_chars: int) -> str:
    if target_chars <= 0:
        return text

    cap = max(len(text), int(target_chars * 1.25))
    additions = [
        "Check whether the content is informational, corrective, persuasive, or instructive before choosing an action.",
        "Treat concrete current claims about election operations as higher risk than general opinion or historical discussion.",
        "Prefer context for repeatable rumors when correction is useful; prefer removal for endorsed false operational claims.",
        "Use escalation when coordination, targeted mobilization, or immediate offline consequences make the policy boundary uncertain.",
    ]
    expanded = text
    index = 0
    while len(expanded) < target_chars and len(expanded) < cap:
        candidate = f"{expanded}\n{additions[index % len(additions)]}"
        if len(candidate) > cap:
            break
        expanded = candidate
        index += 1

    if len(expanded) <= cap:
        return expanded
    return expanded[:cap].rsplit(" ", 1)[0].rstrip(". ,;") + "."


def _rewrite_rule(
    rule_id: str,
    raw_rule: Any,
    mode: str,
    target_chars: int,
) -> str:
    rewritten = _template_rewrite_rule(rule_id, raw_rule)
    if mode == "length_matched":
        rewritten = _fit_to_length(rewritten, target_chars)
    return _sanitize_text(rewritten)


def compile_rewrite_baseline_collection(
    source_policies: dict[str, Any],
    target_policies: dict[str, Any],
    mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if mode not in MODES:
        raise ValueError(f"Unknown rewrite baseline mode: {mode}")

    target_avg = _average_rule_chars(target_policies)
    compiled: dict[str, Any] = {}
    for policy_id, policy in source_policies.items():
        rules = policy.get("rules", {}) if isinstance(policy, dict) else {}
        rewritten_rules = {
            str(rule_id): _rewrite_rule(
                str(rule_id),
                raw_rule,
                mode,
                _target_rule_length(target_policies, str(policy_id), str(rule_id), int(target_avg)),
            )
            for rule_id, raw_rule in rules.items()
        }
        name = str(policy.get("name", policy_id)) if isinstance(policy, dict) else str(policy_id)
        description = str(policy.get("description", "")) if isinstance(policy, dict) else ""
        label = "Length-Matched Rewrite" if mode == "length_matched" else "Template Rewrite"
        compiled[str(policy_id)] = {
            "name": _sanitize_text(f"{label} {name}"),
            "description": _sanitize_text(description),
            "rules": rewritten_rules,
        }

    sidecar = {
        "artifact_type": "rewrite_baseline_policy",
        "mode": mode,
        "uses_cases": False,
        "source_avg_rule_chars": _average_rule_chars(source_policies),
        "target_avg_rule_chars": target_avg,
        "output_avg_rule_chars": _average_rule_chars(compiled),
    }
    return compiled, sidecar


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic LLM/prompt rewrite baseline policies.",
    )
    parser.add_argument("--source-policies", required=True, help="Abstract source policy JSON.")
    parser.add_argument("--target-policies", required=True, help="Target policy JSON used for length statistics.")
    parser.add_argument("--output-policies", required=True, help="Output runner-compatible policy JSON.")
    parser.add_argument("--output-sidecar", required=True, help="Output rewrite baseline sidecar JSON.")
    parser.add_argument("--mode", choices=MODES, required=True)
    args = parser.parse_args(argv)

    source_policies = json.loads(Path(args.source_policies).read_text(encoding="utf-8"))
    target_policies = json.loads(Path(args.target_policies).read_text(encoding="utf-8"))
    compiled, sidecar = compile_rewrite_baseline_collection(
        source_policies,
        target_policies,
        mode=args.mode,
    )
    _write_json(Path(args.output_policies), compiled)
    _write_json(Path(args.output_sidecar), sidecar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
