from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ZERO_RATES = {
    "policy_only_boundary_error_rate": 0.0,
    "policy_only_exact_action_error_rate": 0.0,
    "policy_only_decision_family_error_rate": 0.0,
    "policy_only_action_granularity_error_rate": 0.0,
    "action_granularity_rescue_rate": 0.0,
    "current_guidance_rescue_rate": 0.0,
    "stale_guidance_harm_rate": 0.0,
    "boundary_instability_rate": 0.0,
    "invalid_used_precedent_rate": 0.0,
}


def _empty_result() -> dict[str, Any]:
    return {
        "n_cases": 0,
        "n_rows": 0,
        **ZERO_RATES,
        "stale_rationale_match_total": 0,
        "pseudo_consensus_candidates": [],
        "family_summaries": {},
        "per_case": {},
    }


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _row_condition(group_condition: str | None, row: dict[str, Any]) -> str:
    return str(row.get("condition") or group_condition or "")


def _row_model(run: dict[str, Any], row: dict[str, Any]) -> str:
    return str(row.get("model") or run.get("model") or "")


def _row_expected_family(row: dict[str, Any]) -> str | None:
    family = row.get("expected_decision_family", row.get("expected_family"))
    return str(family) if family is not None else None


def _row_model_family(row: dict[str, Any]) -> str | None:
    family = row.get("model_decision_family", row.get("decision_family"))
    return str(family) if family is not None else None


def _extract_metadata_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    for part in text.split(";"):
        stripped = part.strip()
        if stripped.startswith(prefix):
            value = stripped[len(prefix) :].strip()
            return value or None
    return None


def load_case_metadata(paths: list[str]) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    for path in paths:
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                record = json.loads(stripped)
                case_id = str(record.get("case_id", ""))
                if not case_id:
                    continue
                rationale = str(record.get("expected_rationale", ""))
                case_metadata = {
                    "boundary_family": _extract_metadata_value(rationale, "boundary_family")
                    or "unknown",
                    "hidden_anchor_label": _extract_metadata_value(
                        rationale,
                        "hidden_anchor_label",
                    )
                    or "unknown",
                }
                metadata[case_id] = case_metadata
    return metadata


def _flatten_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_rows = []
    for run_index, run in enumerate(runs):
        rows = run.get("rows", {})
        if isinstance(rows, dict):
            condition_items = rows.items()
        elif isinstance(rows, list):
            condition_items = [(None, rows)]
        else:
            condition_items = []

        for group_condition, condition_rows in condition_items:
            for row in condition_rows:
                enriched = dict(row)
                enriched["_run_index"] = run_index
                enriched["_model"] = _row_model(run, row)
                enriched["_condition"] = _row_condition(group_condition, row)
                enriched["_memory_view"] = run.get("memory_view")
                enriched["_policy_view"] = run.get("policy_view")
                enriched["_stale_warning"] = run.get("stale_warning")
                flat_rows.append(enriched)
    return flat_rows


def _is_policy_adherent(row: dict[str, Any]) -> bool | None:
    value = row.get("policy_adherence")
    if isinstance(value, bool):
        return value
    return None


def _per_case(flat_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for row in flat_rows:
        case_id = row.get("case_id")
        if case_id is None:
            continue
        case_key = str(case_id)
        condition = row["_condition"]
        model_family = _row_model_family(row)
        expected_family = _row_expected_family(row)
        expected_decision = str(row.get("expected_decision", "")) or None
        model_decision = str(row.get("model_decision", "")) or None
        policy_adherence = _is_policy_adherent(row)
        family_adherence = (
            model_family == expected_family
            if model_family is not None and expected_family is not None
            else None
        )

        diagnostic = cases.setdefault(
            case_key,
            {
                "case_id": case_key,
                "expected_decision": expected_decision,
                "expected_decision_family": expected_family,
                "model_decisions": [],
                "decision_families": [],
                "conditions": {},
                "policy_only_correct": None,
                "policy_only_exact_correct": None,
                "policy_only_family_correct": None,
                "regime_aware_correct": None,
                "regime_aware_exact_correct": None,
                "regime_aware_family_correct": None,
                "naive_memory_correct": None,
                "naive_memory_exact_correct": None,
                "naive_memory_family_correct": None,
                "invalid_used_precedent_rows": 0,
                "stale_rationale_match_total": 0,
                "rows": [],
            },
        )
        if diagnostic["expected_decision"] is None and expected_decision is not None:
            diagnostic["expected_decision"] = expected_decision
        if diagnostic["expected_decision_family"] is None and expected_family is not None:
            diagnostic["expected_decision_family"] = expected_family
        if model_decision is not None and model_decision not in diagnostic["model_decisions"]:
            diagnostic["model_decisions"].append(model_decision)
        if model_family is not None and model_family not in diagnostic["decision_families"]:
            diagnostic["decision_families"].append(model_family)

        if policy_adherence is not None:
            if condition == "policy_only":
                diagnostic["policy_only_correct"] = (
                    bool(diagnostic["policy_only_correct"]) or policy_adherence
                )
                diagnostic["policy_only_exact_correct"] = (
                    bool(diagnostic["policy_only_exact_correct"]) or policy_adherence
                )
            elif condition == "regime_aware":
                diagnostic["regime_aware_correct"] = (
                    bool(diagnostic["regime_aware_correct"]) or policy_adherence
                )
                diagnostic["regime_aware_exact_correct"] = (
                    bool(diagnostic["regime_aware_exact_correct"]) or policy_adherence
                )
            elif condition == "naive_memory":
                diagnostic["naive_memory_correct"] = (
                    bool(diagnostic["naive_memory_correct"]) or policy_adherence
                )
                diagnostic["naive_memory_exact_correct"] = (
                    bool(diagnostic["naive_memory_exact_correct"]) or policy_adherence
                )
        if family_adherence is not None:
            if condition == "policy_only":
                diagnostic["policy_only_family_correct"] = (
                    bool(diagnostic["policy_only_family_correct"]) or family_adherence
                )
            elif condition == "regime_aware":
                diagnostic["regime_aware_family_correct"] = (
                    bool(diagnostic["regime_aware_family_correct"]) or family_adherence
                )
            elif condition == "naive_memory":
                diagnostic["naive_memory_family_correct"] = (
                    bool(diagnostic["naive_memory_family_correct"]) or family_adherence
                )

        invalid_count = int(row.get("invalid_used_precedent_count", 0) or 0)
        stale_count = int(row.get("stale_rationale_match_count", 0) or 0)
        if invalid_count > 0:
            diagnostic["invalid_used_precedent_rows"] += 1
        diagnostic["stale_rationale_match_total"] += stale_count

        condition_diagnostic = diagnostic["conditions"].setdefault(
            condition,
            {"models": [], "n_rows": 0, "decisions": [], "decision_families": []},
        )
        condition_diagnostic["n_rows"] += 1
        if row["_model"] not in condition_diagnostic["models"]:
            condition_diagnostic["models"].append(row["_model"])
        if model_decision is not None and model_decision not in condition_diagnostic["decisions"]:
            condition_diagnostic["decisions"].append(model_decision)
        if model_family is not None and model_family not in condition_diagnostic["decision_families"]:
            condition_diagnostic["decision_families"].append(model_family)

        diagnostic["rows"].append(
            {
                "run_index": row["_run_index"],
                "model": row["_model"],
                "condition": condition,
                "memory_view": row["_memory_view"],
                "policy_view": row["_policy_view"],
                "stale_warning": row["_stale_warning"],
                "expected_decision": expected_decision,
                "model_decision": model_decision,
                "expected_decision_family": expected_family,
                "model_decision_family": model_family,
                "policy_adherence": policy_adherence,
                "decision_family_adherence": family_adherence,
                "invalid_used_precedent_count": invalid_count,
                "stale_rationale_match_count": stale_count,
            }
        )
    return cases


def _attach_case_metadata(
    per_case: dict[str, dict[str, Any]],
    case_metadata: dict[str, dict[str, str]],
) -> None:
    for case_id, diagnostic in per_case.items():
        metadata = case_metadata.get(case_id, {})
        diagnostic["boundary_family"] = metadata.get("boundary_family", "unknown")
        diagnostic["hidden_anchor_label"] = metadata.get("hidden_anchor_label", "unknown")


def _pseudo_consensus_candidates(per_case: dict[str, dict[str, Any]]) -> list[str]:
    candidates = []
    for case_id, diagnostic in per_case.items():
        expected_family = diagnostic["expected_decision_family"]
        non_policy_families = [
            row["model_decision_family"]
            for row in diagnostic["rows"]
            if row["condition"] != "policy_only" and row["model_decision_family"] is not None
        ]
        unique_families = set(non_policy_families)
        if (
            expected_family is not None
            and len(non_policy_families) >= 2
            and len(unique_families) == 1
            and next(iter(unique_families)) != expected_family
        ):
            candidates.append(case_id)
    return sorted(candidates)


def _summarize(flat_rows: list[dict[str, Any]], per_case: dict[str, dict[str, Any]]) -> dict[str, Any]:
    n_cases = len(per_case)
    if n_cases == 0:
        return _empty_result()

    policy_only_rows = [row for row in flat_rows if row["_condition"] == "policy_only"]
    policy_only_exact_wrong_rows = [
        row for row in policy_only_rows if row.get("policy_adherence") is False
    ]
    policy_only_family_wrong_rows = [
        row
        for row in policy_only_rows
        if _row_model_family(row) is not None
        and _row_expected_family(row) is not None
        and _row_model_family(row) != _row_expected_family(row)
    ]
    policy_only_action_granularity_wrong_rows = [
        row
        for row in policy_only_exact_wrong_rows
        if _row_model_family(row) is not None
        and _row_expected_family(row) is not None
        and _row_model_family(row) == _row_expected_family(row)
    ]
    invalid_used_rows = [
        row for row in flat_rows if int(row.get("invalid_used_precedent_count", 0) or 0) > 0
    ]
    stale_rationale_match_total = sum(
        int(row.get("stale_rationale_match_count", 0) or 0) for row in flat_rows
    )

    policy_only_wrong_cases = [
        diagnostic
        for diagnostic in per_case.values()
        if any(
            row["condition"] == "policy_only" and row["policy_adherence"] is False
            for row in diagnostic["rows"]
        )
    ]
    policy_only_correct_cases = [
        diagnostic
        for diagnostic in per_case.values()
        if any(
            row["condition"] == "policy_only" and row["policy_adherence"] is True
            for row in diagnostic["rows"]
        )
    ]

    rescued_cases = [
        diagnostic
        for diagnostic in policy_only_wrong_cases
        if any(
            row["condition"] == "regime_aware" and row["policy_adherence"] is True
            for row in diagnostic["rows"]
        )
    ]
    harmed_cases = [
        diagnostic
        for diagnostic in policy_only_correct_cases
        if any(
            row["condition"] == "naive_memory" and row["policy_adherence"] is False
            for row in diagnostic["rows"]
        )
    ]
    policy_only_action_granularity_wrong_cases = [
        diagnostic
        for diagnostic in per_case.values()
        if any(
            row["condition"] == "policy_only"
            and row["policy_adherence"] is False
            and row["decision_family_adherence"] is True
            for row in diagnostic["rows"]
        )
    ]
    action_granularity_rescued_cases = [
        diagnostic
        for diagnostic in policy_only_action_granularity_wrong_cases
        if any(
            row["condition"] == "regime_aware" and row["policy_adherence"] is True
            for row in diagnostic["rows"]
        )
    ]
    unstable_cases = [
        diagnostic for diagnostic in per_case.values() if len(diagnostic["decision_families"]) > 1
    ]

    return {
        "n_cases": n_cases,
        "n_rows": len(flat_rows),
        "policy_only_boundary_error_rate": _rate(
            sum(1 for row in policy_only_rows if row.get("policy_adherence") is False),
            len(policy_only_rows),
        ),
        "policy_only_exact_action_error_rate": _rate(
            len(policy_only_exact_wrong_rows),
            len(policy_only_rows),
        ),
        "policy_only_decision_family_error_rate": _rate(
            len(policy_only_family_wrong_rows),
            len(policy_only_rows),
        ),
        "policy_only_action_granularity_error_rate": _rate(
            len(policy_only_action_granularity_wrong_rows),
            len(policy_only_rows),
        ),
        "action_granularity_rescue_rate": _rate(
            len(action_granularity_rescued_cases),
            len(policy_only_action_granularity_wrong_cases),
        ),
        "current_guidance_rescue_rate": _rate(len(rescued_cases), len(policy_only_wrong_cases)),
        "stale_guidance_harm_rate": _rate(len(harmed_cases), len(policy_only_correct_cases)),
        "boundary_instability_rate": _rate(len(unstable_cases), n_cases),
        "invalid_used_precedent_rate": _rate(len(invalid_used_rows), len(flat_rows)),
        "stale_rationale_match_total": stale_rationale_match_total,
        "pseudo_consensus_candidates": _pseudo_consensus_candidates(per_case),
    }


def _family_summaries(
    flat_rows: list[dict[str, Any]],
    per_case: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    families = sorted(
        {
            str(diagnostic.get("boundary_family", "unknown"))
            for diagnostic in per_case.values()
        }
    )
    summaries: dict[str, dict[str, Any]] = {}
    for family in families:
        family_case_ids = {
            case_id
            for case_id, diagnostic in per_case.items()
            if diagnostic.get("boundary_family", "unknown") == family
        }
        family_rows = [
            row for row in flat_rows if str(row.get("case_id", "")) in family_case_ids
        ]
        family_cases = {
            case_id: diagnostic
            for case_id, diagnostic in per_case.items()
            if case_id in family_case_ids
        }
        summaries[family] = _summarize(family_rows, family_cases)
    return summaries


def analyze_runs(
    runs: list[dict[str, Any]],
    case_metadata: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    flat_rows = _flatten_rows(runs)
    per_case = _per_case(flat_rows)
    _attach_case_metadata(per_case, case_metadata or {})
    if not per_case:
        return _empty_result()
    result = _summarize(flat_rows, per_case)
    result["family_summaries"] = _family_summaries(flat_rows, per_case)
    result["per_case"] = per_case
    return result


def load_runs(paths: list[str]) -> list[dict[str, Any]]:
    runs = []
    for path in paths:
        runs.append(json.loads(Path(path).read_text(encoding="utf-8")))
    return runs


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="*", default=[])
    parser.add_argument("--cases", nargs="*", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    result = analyze_runs(load_runs(args.inputs), load_case_metadata(args.cases))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
