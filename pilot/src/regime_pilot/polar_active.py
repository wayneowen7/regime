from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from regime_pilot.schema import load_jsonl


ACTION_ORDER = ["allow", "contextualize", "restrict", "remove", "escalate"]


@dataclass(frozen=True)
class GapReport:
    gap_id: str
    regime_id: str
    rule_id: str
    boundary_family: str
    action_contrast: str
    gap_type: str
    error_pairs: list[str]
    affected_case_ids: list[str]
    candidate_cues: list[str]
    harm_direction: str
    confidence: float


@dataclass(frozen=True)
class IRPatch:
    patch_id: str
    gap_id: str
    regime_id: str
    patch_type: str
    rule_id: str
    boundary_family: str
    action_contrast: str
    selected_cues: list[str]
    target_error_pairs: list[str]
    instruction: str
    expected_effect: str


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


def _split_variables(value: str) -> list[str]:
    variables: list[str] = []
    for item in value.split("|"):
        stripped = item.strip()
        if stripped and stripped not in variables:
            variables.append(stripped)
    return variables


def parse_case_metadata(case: dict[str, Any]) -> dict[str, Any]:
    metadata = _metadata_from_rationale(str(case.get("expected_rationale", "")))
    return {
        "boundary_family": metadata.get("boundary_family", "unknown"),
        "action_contrast": metadata.get("action_contrast", "unknown"),
        "boundary_variables": _split_variables(metadata.get("boundary_variables", "")),
    }


def decision_severity(decision: str) -> int:
    try:
        return ACTION_ORDER.index(decision)
    except ValueError:
        return -1


def _classify_gap(row: dict[str, Any]) -> tuple[str, str]:
    expected = str(row.get("expected_decision", ""))
    observed = str(row.get("model_decision", ""))
    family_ok = bool(row.get("decision_family_adherence"))
    if not family_ok:
        gap_type = "missing_boundary"
    else:
        gap_type = "missing_action_edge"

    expected_severity = decision_severity(expected)
    observed_severity = decision_severity(observed)
    if observed_severity > expected_severity >= 0:
        harm_direction = "over_removal"
    elif 0 <= observed_severity < expected_severity:
        harm_direction = "under_enforcement"
    else:
        harm_direction = "wrong_action_granularity"
    if gap_type == "missing_action_edge":
        harm_direction = "wrong_action_granularity"
    return gap_type, harm_direction


def _case_index(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(case.get("case_id")): case for case in cases}


def localize_gaps_from_rows(
    rows: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    policy_condition: str,
) -> list[GapReport]:
    cases_by_id = _case_index(cases)
    groups: dict[tuple[str, str, str, str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "affected_case_ids": [],
            "candidate_cues": [],
            "error_pairs": [],
            "count": 0,
        }
    )

    for row in rows:
        if str(row.get("policy_condition", policy_condition)) != policy_condition:
            continue
        if bool(row.get("policy_adherence")):
            continue
        case_id = str(row.get("case_id", ""))
        case = cases_by_id.get(case_id, {})
        metadata = parse_case_metadata(case)
        gap_type, harm_direction = _classify_gap(row)
        expected = str(row.get("expected_decision", "unknown"))
        observed = str(row.get("model_decision", "unknown"))
        error_pair = f"{expected}->{observed}"
        regime_id = str(case.get("active_regime_id") or row.get("active_regime_id") or "unknown")
        rule_id = str(case.get("policy_rule") or row.get("policy_rule") or "unknown")
        key = (
            regime_id,
            rule_id,
            metadata["boundary_family"],
            metadata["action_contrast"],
            gap_type,
            error_pair,
            harm_direction,
        )
        group = groups[key]
        if case_id and case_id not in group["affected_case_ids"]:
            group["affected_case_ids"].append(case_id)
        if error_pair not in group["error_pairs"]:
            group["error_pairs"].append(error_pair)
        for cue in metadata["boundary_variables"]:
            if cue not in group["candidate_cues"]:
                group["candidate_cues"].append(cue)
        group["count"] += 1

    reports: list[GapReport] = []
    gap_order = {"missing_boundary": 0, "missing_action_edge": 1}
    sorted_groups = sorted(
        groups.items(),
        key=lambda item: (
            gap_order.get(item[0][4], 99),
            item[0][0],
            item[0][1],
            item[0][2],
            item[0][3],
            item[0][5],
            item[0][6],
        ),
    )
    for index, (key, group) in enumerate(sorted_groups, start=1):
        regime_id, rule_id, boundary_family, action_contrast, gap_type, _error_pair, harm_direction = key
        affected_count = len(group["affected_case_ids"]) or 1
        confidence = min(1.0, group["count"] / affected_count)
        reports.append(
            GapReport(
                gap_id=f"gap-{index:04d}",
                regime_id=regime_id,
                rule_id=rule_id,
                boundary_family=boundary_family,
                action_contrast=action_contrast,
                gap_type=gap_type,
                error_pairs=list(group["error_pairs"]),
                affected_case_ids=list(group["affected_case_ids"]),
                candidate_cues=list(group["candidate_cues"]),
                harm_direction=harm_direction,
                confidence=confidence,
            )
        )
    return reports


def _expected_actions(error_pairs: list[str]) -> list[str]:
    actions: list[str] = []
    for pair in error_pairs:
        expected, _, _observed = pair.partition("->")
        expected = expected.strip()
        if expected and expected not in actions:
            actions.append(expected)
    return actions


def _observed_actions(error_pairs: list[str]) -> list[str]:
    actions: list[str] = []
    for pair in error_pairs:
        _expected, arrow, observed = pair.partition("->")
        if not arrow:
            continue
        observed = observed.strip()
        if observed and observed not in actions:
            actions.append(observed)
    return actions


def propose_patches(
    gaps: list[GapReport],
    max_patches: int = 8,
    max_cues_per_patch: int = 5,
) -> list[IRPatch]:
    patches: list[IRPatch] = []
    for gap in gaps[:max_patches]:
        selected_cues = gap.candidate_cues[:max_cues_per_patch]
        cue_text = " + ".join(selected_cues) if selected_cues else "the affected boundary cues"
        expected_actions = "/".join(_expected_actions(gap.error_pairs)) or "the expected action"
        observed_actions = "/".join(_observed_actions(gap.error_pairs)) or "the observed wrong action"
        if gap.gap_type == "missing_boundary":
            patch_type = "add_boundary_variable"
            instruction = (
                f"If {cue_text} match {gap.boundary_family}, choose {expected_actions} "
                f"over {observed_actions} at the {gap.action_contrast} boundary."
            )
        elif gap.gap_type == "missing_action_edge":
            patch_type = "add_action_edge"
            instruction = (
                f"If the decision family is right but the action is unstable, use {cue_text} "
                f"to choose {expected_actions} over {observed_actions}."
            )
        else:
            patch_type = "add_priority_rule"
            instruction = (
                f"Check {cue_text} before choosing {expected_actions} for {gap.boundary_family}."
            )
        patches.append(
            IRPatch(
                patch_id=f"patch-{len(patches) + 1:04d}",
                gap_id=gap.gap_id,
                regime_id=gap.regime_id,
                patch_type=patch_type,
                rule_id=gap.rule_id,
                boundary_family=gap.boundary_family,
                action_contrast=gap.action_contrast,
                selected_cues=selected_cues,
                target_error_pairs=list(gap.error_pairs),
                instruction=instruction,
                expected_effect=(
                    f"Reduce {gap.harm_direction} for {gap.boundary_family} "
                    f"cases affected by {', '.join(gap.error_pairs)}."
                ),
            )
        )
    return patches


def _append_patch_lines_with_budget(
    base_text: str,
    patch_lines: list[str],
    length_budget_chars: int,
) -> tuple[str, int]:
    if not patch_lines or len(base_text) >= length_budget_chars:
        return base_text, 0

    header = "\nPOLAR-Active patches:"
    compiled = base_text
    applied = 0
    for line in patch_lines:
        addition = header + "\n" + line if applied == 0 else "\n" + line
        if len(compiled) + len(addition) > length_budget_chars:
            break
        compiled += addition
        applied += 1
    return compiled, applied


def _format_patch_line(patch: IRPatch) -> str:
    cues = "+".join(patch.selected_cues) or "none"
    return f"- {patch.patch_id} {patch.patch_type}; cues={cues}; {patch.instruction}"


def apply_patches_to_policies(
    policies: dict[str, Any],
    patches: list[IRPatch],
    length_budget_chars: int = 3600,
) -> tuple[dict[str, Any], dict[str, Any]]:
    patch_index: dict[tuple[str, str], list[IRPatch]] = defaultdict(list)
    for patch in patches:
        patch_index[(patch.regime_id, patch.rule_id)].append(patch)

    compiled: dict[str, Any] = {}
    patched_rule_count = 0
    applied_patch_count = 0
    dropped_patch_ids: list[str] = []
    for policy_id, policy in policies.items():
        compiled_rules: dict[str, Any] = {}
        for rule_id, rule_text in policy.get("rules", {}).items():
            text = str(rule_text)
            rule_patches = patch_index.get((str(policy_id), str(rule_id)), [])
            if rule_patches:
                patch_lines = [_format_patch_line(patch) for patch in rule_patches]
                text, applied_count = _append_patch_lines_with_budget(
                    text,
                    patch_lines,
                    length_budget_chars,
                )
                if applied_count > 0:
                    patched_rule_count += 1
                    applied_patch_count += applied_count
                dropped_patch_ids.extend(patch.patch_id for patch in rule_patches[applied_count:])
            compiled_rules[str(rule_id)] = text
        compiled[str(policy_id)] = {
            "name": f"POLAR-Active {policy.get('name', policy_id)}",
            "description": str(policy.get("description", "")),
            "rules": compiled_rules,
        }

    sidecar = {
        "artifact_type": "polar_active_policy",
        "patch_count": len(patches),
        "applied_patch_count": applied_patch_count,
        "dropped_patch_ids": dropped_patch_ids,
        "patched_rule_count": patched_rule_count,
        "length_budget_chars": length_budget_chars,
        "patches": [patch.__dict__ for patch in patches],
    }
    return compiled, sidecar


def _condition_from_result(data: dict[str, Any], fallback: str) -> str:
    conditions = data.get("conditions", [])
    if isinstance(conditions, list) and conditions:
        return str(conditions[0])
    return fallback


def load_result_rows(paths: list[str | Path], policy_condition: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path_value in paths:
        path = Path(path_value)
        data = json.loads(path.read_text(encoding="utf-8"))
        model = str(data.get("model", "unknown"))
        row_groups = data.get("rows", {})
        if isinstance(row_groups, dict):
            group_items = row_groups.items()
        else:
            group_items = [(_condition_from_result(data, policy_condition), row_groups)]
        for condition, group_rows in group_items:
            if str(condition) != policy_condition:
                continue
            for row in group_rows:
                normalized = dict(row)
                normalized["model"] = model
                normalized["policy_condition"] = str(condition)
                rows.append(normalized)
    return rows


def _gap_to_dict(gap: GapReport) -> dict[str, Any]:
    return gap.__dict__


def _write_json(path: str | Path, value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def compile_polar_active_artifacts(
    policies: dict[str, Any],
    cases: list[dict[str, Any]],
    result_rows: list[dict[str, Any]],
    policy_condition: str,
    max_patches: int = 8,
    length_budget_chars: int = 3600,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    gaps = localize_gaps_from_rows(result_rows, cases, policy_condition=policy_condition)
    patches = propose_patches(gaps, max_patches=max_patches)
    compiled_policies, sidecar = apply_patches_to_policies(
        policies,
        patches,
        length_budget_chars=length_budget_chars,
    )
    gap_report = {
        "artifact_type": "polar_active_gap_report",
        "contains_raw_text": False,
        "policy_condition": policy_condition,
        "gap_count": len(gaps),
        "gaps": [_gap_to_dict(gap) for gap in gaps],
    }
    prompt_lengths = [
        len(str(rule_text))
        for policy in compiled_policies.values()
        for rule_text in policy.get("rules", {}).values()
    ]
    summary = {
        "artifact_type": "polar_active_summary",
        "contains_raw_text": False,
        "policy_condition": policy_condition,
        "case_count": len(cases),
        "result_row_count": len(result_rows),
        "gap_count": len(gaps),
        "patch_count": len(patches),
        "applied_patch_count": sidecar["applied_patch_count"],
        "dropped_patch_count": len(sidecar["dropped_patch_ids"]),
        "patched_rule_count": sidecar["patched_rule_count"],
        "prompt_length": {
            "avg_chars": (sum(prompt_lengths) / len(prompt_lengths)) if prompt_lengths else 0.0,
            "max_chars": max(prompt_lengths) if prompt_lengths else 0,
            "length_budget_chars": length_budget_chars,
        },
        "gap_type_counts": dict(sorted(Counter(gap.gap_type for gap in gaps).items())),
        "harm_direction_counts": dict(sorted(Counter(gap.harm_direction for gap in gaps).items())),
    }
    sidecar["contains_raw_text"] = False
    return compiled_policies, sidecar, gap_report, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile POLAR-Active patched policies.")
    parser.add_argument("--policies", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--results", nargs="+", required=True)
    parser.add_argument("--policy-condition", default="policy_only")
    parser.add_argument("--output-policies", required=True)
    parser.add_argument("--output-sidecar", required=True)
    parser.add_argument("--output-gap-report", required=True)
    parser.add_argument("--output-summary", required=True)
    parser.add_argument("--max-patches", type=int, default=8)
    parser.add_argument("--length-budget-chars", type=int, default=3600)
    args = parser.parse_args(argv)

    policies = json.loads(Path(args.policies).read_text(encoding="utf-8"))
    cases = load_jsonl(args.cases)
    rows = load_result_rows(args.results, policy_condition=args.policy_condition)
    compiled, sidecar, gap_report, summary = compile_polar_active_artifacts(
        policies=policies,
        cases=cases,
        result_rows=rows,
        policy_condition=args.policy_condition,
        max_patches=args.max_patches,
        length_budget_chars=args.length_budget_chars,
    )
    _write_json(args.output_policies, compiled)
    _write_json(args.output_sidecar, sidecar)
    _write_json(args.output_gap_report, gap_report)
    _write_json(args.output_summary, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
