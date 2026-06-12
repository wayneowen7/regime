from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Protocol

from regime_pilot.ollama_client import OllamaClient


JUDGE_VARIANTS = ("policy_clause", "boundary_variable", "skeptical_anchor")


class GenerationClient(Protocol):
    def generate(self, model: str, prompt: str) -> str:
        ...


def _format_policy(policy: dict[str, Any]) -> str:
    rules = policy.get("rules", {})
    rule_lines = "\n".join(
        f"- {name}: {_format_policy_value(text)}" for name, text in sorted(rules.items())
    )
    return (
        f"name: {policy.get('name', '')}\n"
        f"description: {policy.get('description', '')}\n"
        f"rules:\n{rule_lines}"
    )


def _format_policy_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def build_generation_prompt(
    policy: dict[str, Any],
    boundary_family: str,
    num_candidates: int,
) -> str:
    return f"""You are helping audit policy reliability.

This is diagnostic boundary probe generation, not synthetic training data generation.
Generate a small set of contrastive/boundary cases that probe whether the policy boundary is underspecified.
Do not create large-scale samples, training corpora, or model-tuning data.

Policy:
{_format_policy(policy)}

Boundary family to probe: {boundary_family}
Number of candidates: {num_candidates}

Return JSON only: an array of objects.
Each object must contain:
- "content": the short candidate content or scenario
- "proposed_label": your tentative policy label
- "rationale": why this probes a boundary
- optional "boundary_variable": the policy boundary variable being probed
- optional "policy_clause": the policy rule or exception that supports the label
- optional "ambiguous": true when the case is intentionally ambiguous

Required JSON shape:
[
  {{"content":"short boundary case","proposed_label":"allow","rationale":"short reason","boundary_variable":"short variable","policy_clause":"short clause"}}
]
"""


def _judge_variant_instruction(variant: str) -> str:
    if variant == "policy_clause":
        return "Focus on whether the label is directly supported by an explicit current policy clause."
    if variant == "boundary_variable":
        return "Focus on whether the case confuses two boundary variables that the policy treats differently."
    if variant == "skeptical_anchor":
        return "Be skeptical of labels that fill in a boundary not stated by the current policy."
    return "Judge conservatively against the explicit current policy text."


def build_judge_prompt(
    policy: dict[str, Any],
    candidate: dict[str, Any],
    variant: str = "policy_clause",
) -> str:
    return f"""You are judging one diagnostic boundary probe against the current policy.

This is reliability auditing, not training data creation.
Judge variant: {variant}
{_judge_variant_instruction(variant)}

Policy:
{_format_policy(policy)}

Candidate:
content: {candidate.get('content', '')}
generator_proposed_label: {candidate.get('proposed_label', '')}
generator_rationale: {candidate.get('rationale', '')}

Return JSON only with:
- "label": your policy label for this candidate
- "rationale": concise reason grounded in the policy
- "policy_clause_support": true only if your label is directly supported by an explicit current policy clause
- "boundary_variable_confusion": true if the candidate or proposed label appears to confuse policy boundary variables
- "needs_policy_owner_anchor": true if the current policy is not sufficient to decide without an owner clarification

Required JSON shape:
{{"label":"remove","rationale":"short reason","policy_clause_support":true,"boundary_variable_confusion":false,"needs_policy_owner_anchor":false}}
"""


def _extract_json_value(text: str, expected_type: type) -> Any:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, expected_type):
            return value
    raise ValueError(f"No JSON {expected_type.__name__} found")


def parse_json_list(text: str) -> list[dict[str, Any]]:
    try:
        value = _extract_json_value(text, list)
    except ValueError:
        singleton = _extract_json_value(text, dict)
        return [singleton]
    return [item for item in value if isinstance(item, dict)]


def parse_json_object(text: str) -> dict[str, Any]:
    return _extract_json_value(text, dict)


def _candidate_id(family: str, index: int) -> str:
    return f"{family}-{index:03d}"


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _invalid_candidate_reasons(candidate: dict[str, Any]) -> list[str]:
    reasons = []
    for field in ("content", "proposed_label", "rationale"):
        if not str(candidate.get(field, "")).strip():
            reasons.append(f"missing_{field}")
    return reasons


def _normalized_content(candidate: dict[str, Any]) -> str:
    return " ".join(str(candidate.get("content", "")).lower().split())


def _candidate_anchor_label(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("anchor_label")
        or candidate.get("expected_current_boundary")
        or candidate.get("expected_label")
        or ""
    )


def _is_ambiguous_candidate(candidate: dict[str, Any]) -> bool:
    if candidate.get("ambiguous") is True:
        return True
    joined = " ".join(
        str(candidate.get(field, ""))
        for field in ("content", "proposed_label", "rationale")
    ).lower()
    return "ambiguous" in joined or "underspecified" in joined


def _summarize_family(
    family: str,
    candidates: list[dict[str, Any]],
    judge_results: list[dict[str, Any]],
    requested_count: int,
    invalid_candidates: list[dict[str, Any]],
    generation_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    results_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in judge_results:
        results_by_candidate[str(result["candidate_id"])].append(result)

    agreed = 0
    judged = 0
    labels = set()
    anchor_matches = 0
    anchor_judgments = 0
    support_values = []
    confusion_values = []
    parse_errors = 0
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        labels.add(str(candidate.get("proposed_label", "")))
        candidate_results = results_by_candidate[candidate_id]
        parse_errors += sum(1 for item in candidate_results if item.get("parse_error"))
        parsed_results = [item for item in candidate_results if not item.get("parse_error")]
        judge_labels = [str(item.get("label", "")) for item in parsed_results]
        labels.update(label for label in judge_labels if label)
        if len(judge_labels) >= 2:
            judged += 1
        if len(judge_labels) >= 2 and len(set(judge_labels)) == 1:
            agreed += 1
        anchor_label = _candidate_anchor_label(candidate)
        if anchor_label:
            for label in judge_labels:
                anchor_judgments += 1
                if label == anchor_label:
                    anchor_matches += 1
        for item in parsed_results:
            support = _as_bool(item.get("policy_clause_support"))
            if support is not None:
                support_values.append(support)
            confusion = _as_bool(item.get("boundary_variable_confusion"))
            if confusion is not None:
                confusion_values.append(confusion)

    contents = [_normalized_content(candidate) for candidate in candidates]
    non_empty_contents = [content for content in contents if content]
    duplicate_count = len(non_empty_contents) - len(set(non_empty_contents))
    invalid_reason_counts = Counter(
        reason
        for candidate in invalid_candidates
        if candidate.get("family") == family
        for reason in candidate.get("invalid_reasons", [])
    )
    family_generation_errors = [
        item for item in generation_errors if item.get("family") == family
    ]
    attempted_judgments = sum(len(results_by_candidate[str(candidate["candidate_id"])]) for candidate in candidates)

    return {
        "sample_count": len(candidates),
        "n_requested": requested_count,
        "n_valid_candidates": len(candidates),
        "n_invalid_candidates": sum(1 for item in invalid_candidates if item.get("family") == family),
        "sample_yield": _rate(len(candidates), requested_count),
        "duplicate_rate": _rate(duplicate_count, len(non_empty_contents)),
        "invalid_candidate_reasons": dict(sorted(invalid_reason_counts.items())),
        "generation_parse_error_count": len(family_generation_errors),
        "judge_agreement_rate": _rate(agreed, judged),
        "judge_parse_error_rate": _rate(parse_errors, attempted_judgments),
        "anchor_agreement_rate": _rate(anchor_matches, anchor_judgments),
        "anchor_labeled_judgment_count": anchor_judgments,
        "policy_clause_support_rate": _rate(
            sum(1 for value in support_values if value),
            len(support_values),
        ),
        "boundary_variable_confusion_rate": _rate(
            sum(1 for value in confusion_values if value),
            len(confusion_values),
        ),
        "label_diversity": sorted(label for label in labels if label),
    }


def _pseudo_consensus_candidates(
    candidates: list[dict[str, Any]],
    judge_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in judge_results:
        results_by_candidate[str(result["candidate_id"])].append(result)

    flagged = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        parsed_results = [
            item for item in results_by_candidate[candidate_id] if not item.get("parse_error")
        ]
        judge_labels = [str(item.get("label", "")) for item in parsed_results]
        label_counts = Counter(label for label in judge_labels if label)
        unanimous_label = None
        if len(judge_labels) > 1 and len(label_counts) == 1:
            unanimous_label = next(iter(label_counts))
        anchor_label = _candidate_anchor_label(candidate)
        anchor_conflict = (
            unanimous_label is not None
            and bool(anchor_label)
            and anchor_label != unanimous_label
        )
        if anchor_conflict:
            flagged.append(
                {
                    "candidate_id": candidate_id,
                    "family": candidate["family"],
                    "content": candidate["content"],
                    "proposed_label": candidate.get("proposed_label", ""),
                    "anchor_label": anchor_label,
                    "unanimous_judge_label": unanimous_label,
                    "judge_labels": judge_labels,
                    "reason": "unanimous_judge_conflicts_with_anchor_label",
                }
            )
    return flagged


def _manual_review_candidates(
    candidates: list[dict[str, Any]],
    judge_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    results_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in judge_results:
        results_by_candidate[str(result["candidate_id"])].append(result)

    flagged = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        parsed_results = [
            item for item in results_by_candidate[candidate_id] if not item.get("parse_error")
        ]
        judge_labels = [str(item.get("label", "")) for item in parsed_results if item.get("label")]
        if len(judge_labels) < 2 or len(set(judge_labels)) != 1:
            continue
        support_values = [
            _as_bool(item.get("policy_clause_support")) for item in parsed_results
        ]
        confusion_values = [
            _as_bool(item.get("boundary_variable_confusion")) for item in parsed_results
        ]
        low_support = any(value is False for value in support_values)
        confusion = any(value is True for value in confusion_values)
        no_anchor = not _candidate_anchor_label(candidate)
        if low_support or confusion or no_anchor or _is_ambiguous_candidate(candidate):
            flagged.append(
                {
                    "candidate_id": candidate_id,
                    "family": candidate["family"],
                    "content": candidate["content"],
                    "unanimous_judge_label": judge_labels[0],
                    "anchor_label": _candidate_anchor_label(candidate),
                    "reason": "high_agreement_requires_manual_anchor_review",
                }
            )
    return flagged


def _default_judge_variants(count: int) -> list[str]:
    variants = []
    for index in range(count):
        variants.append(JUDGE_VARIANTS[index % len(JUDGE_VARIANTS)])
    return variants


def run_barred_like_audit(
    policies: dict[str, Any],
    families: list[str],
    generator_client: GenerationClient,
    judge_clients: list[GenerationClient],
    model: str,
    num_candidates: int,
    judge_variants: list[str] | None = None,
) -> dict[str, Any]:
    generated_candidates: list[dict[str, Any]] = []
    invalid_candidates: list[dict[str, Any]] = []
    generation_errors: list[dict[str, Any]] = []
    judge_results: list[dict[str, Any]] = []
    judge_errors: list[dict[str, Any]] = []
    policies_in_order = list(policies.values())
    if not policies_in_order:
        raise ValueError("At least one policy is required")
    if not families:
        raise ValueError("At least one boundary family is required")
    if len(judge_clients) < 2:
        raise ValueError("At least two judge clients are required for consensus auditing")
    judge_variants = judge_variants or _default_judge_variants(len(judge_clients))
    if len(judge_variants) != len(judge_clients):
        raise ValueError("judge_variants must match judge_clients length")
    policy = policies_in_order[0]
    policy_regime_id = next(iter(policies))

    for family in families:
        prompt = build_generation_prompt(policy, family, num_candidates)
        raw_candidates = generator_client.generate(model=model, prompt=prompt)
        try:
            parsed_candidates = parse_json_list(raw_candidates)[:num_candidates]
        except ValueError as exc:
            generation_errors.append(
                {
                    "family": family,
                    "error": str(exc),
                    "raw_response": raw_candidates,
                }
            )
            parsed_candidates = []
        family_candidates = []
        for index, candidate in enumerate(parsed_candidates, start=1):
            invalid_reasons = _invalid_candidate_reasons(candidate)
            if invalid_reasons:
                invalid_candidates.append(
                    {
                        "family": family,
                        "candidate_id": _candidate_id(family, index),
                        "invalid_reasons": invalid_reasons,
                        "raw_candidate": candidate,
                    }
                )
                continue
            row = {
                "family": family,
                "candidate_id": _candidate_id(family, index),
                "content": str(candidate.get("content", "")),
                "proposed_label": str(candidate.get("proposed_label", "")),
                "rationale": str(candidate.get("rationale", "")),
            }
            for optional_field in (
                "boundary_variable",
                "policy_clause",
                "anchor_label",
                "expected_current_boundary",
                "expected_label",
            ):
                if optional_field in candidate:
                    row[optional_field] = str(candidate.get(optional_field, ""))
            if candidate.get("ambiguous") is True:
                row["ambiguous"] = True
            generated_candidates.append(row)
            family_candidates.append(row)

        for candidate in family_candidates:
            for judge_index, (judge_client, judge_variant) in enumerate(zip(judge_clients, judge_variants)):
                judge_prompt = build_judge_prompt(policy, candidate, variant=judge_variant)
                raw_judgment = judge_client.generate(model=model, prompt=judge_prompt)
                try:
                    parsed_judgment = parse_json_object(raw_judgment)
                except ValueError as exc:
                    error_row = {
                        "candidate_id": candidate["candidate_id"],
                        "judge_index": judge_index,
                        "judge_variant": judge_variant,
                        "parse_error": True,
                        "error": str(exc),
                        "raw_response": raw_judgment,
                    }
                    judge_errors.append(error_row)
                    judge_results.append(error_row)
                    continue
                judge_results.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "judge_index": judge_index,
                        "judge_variant": judge_variant,
                        "label": str(parsed_judgment.get("label", "")),
                        "rationale": str(parsed_judgment.get("rationale", "")),
                        "policy_clause_support": _as_bool(
                            parsed_judgment.get("policy_clause_support")
                        ),
                        "boundary_variable_confusion": _as_bool(
                            parsed_judgment.get("boundary_variable_confusion")
                        ),
                        "needs_policy_owner_anchor": _as_bool(
                            parsed_judgment.get("needs_policy_owner_anchor")
                        ),
                        "raw_response": raw_judgment,
                    }
                )

    summaries = {}
    for family in families:
        family_candidates = [
            candidate for candidate in generated_candidates if candidate["family"] == family
        ]
        family_ids = {candidate["candidate_id"] for candidate in family_candidates}
        family_judgments = [
            result for result in judge_results if result["candidate_id"] in family_ids
        ]
        summaries[family] = _summarize_family(
            family,
            family_candidates,
            family_judgments,
            num_candidates,
            invalid_candidates,
            generation_errors,
        )

    return {
        "model": model,
        "policy_regime_id": policy_regime_id,
        "judge_agreement_basis": (
            "prompt_variants" if len(set(judge_variants)) > 1 else "repeated_same_prompt"
        ),
        "judge_configs": [
            {"judge_index": index, "model": model, "variant": variant}
            for index, variant in enumerate(judge_variants)
        ],
        "families": families,
        "num_candidates": num_candidates,
        "generated_candidates": generated_candidates,
        "invalid_candidates": invalid_candidates,
        "generation_errors": generation_errors,
        "judge_results": judge_results,
        "judge_errors": judge_errors,
        "summaries": summaries,
        "pseudo_consensus_candidates": _pseudo_consensus_candidates(
            generated_candidates,
            judge_results,
        ),
        "manual_review_candidates": _manual_review_candidates(
            generated_candidates,
            judge_results,
        ),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policies", default="pilot/data/policies.json")
    parser.add_argument("--families", required=True)
    parser.add_argument("--model", default="llama3.2:latest")
    parser.add_argument("--num-candidates", type=int, default=2)
    parser.add_argument("--regime-id", default=None)
    parser.add_argument("--judge-count", type=int, default=2)
    parser.add_argument("--judge-variants", default=None)
    parser.add_argument("--output", default="pilot/results/barred_like.json")
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args(argv)
    if args.judge_count < 2:
        parser.error("--judge-count must be at least 2 for consensus auditing")

    policies = json.loads(Path(args.policies).read_text(encoding="utf-8"))
    families = [item.strip() for item in args.families.split(",") if item.strip()]
    if not families:
        parser.error("--families must include at least one boundary family")
    judge_variants = (
        [item.strip() for item in args.judge_variants.split(",") if item.strip()]
        if args.judge_variants
        else _default_judge_variants(args.judge_count)
    )
    if len(judge_variants) < 2:
        parser.error("--judge-variants must include at least two variants")
    selected_policies = _select_policies(policies, args.regime_id)
    client = OllamaClient(base_url=args.base_url)
    result = run_barred_like_audit(
        policies=selected_policies,
        families=families,
        generator_client=client,
        judge_clients=[client for _ in range(len(judge_variants))],
        model=args.model,
        num_candidates=args.num_candidates,
        judge_variants=judge_variants,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


def _select_policies(policies: dict[str, Any], regime_id: str | None) -> dict[str, Any]:
    if not policies:
        raise ValueError("At least one policy is required")
    if regime_id is not None:
        if regime_id not in policies:
            raise ValueError(f"Unknown regime_id: {regime_id}")
        return {regime_id: policies[regime_id]}
    preferred_regime = "election_integrity_period_v2"
    if preferred_regime in policies:
        return {preferred_regime: policies[preferred_regime]}
    first_regime = next(iter(policies))
    return {first_regime: policies[first_regime]}


if __name__ == "__main__":
    main()
