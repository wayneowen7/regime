from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    "policy_only_boundary_error_rate",
    "policy_only_exact_action_error_rate",
    "policy_only_decision_family_error_rate",
    "policy_only_action_granularity_error_rate",
    "action_granularity_rescue_rate",
    "boundary_instability_rate",
    "current_guidance_rescue_rate",
    "stale_guidance_harm_rate",
    "invalid_used_precedent_rate",
)


def _metric_value(analysis: dict[str, Any], metric: str) -> float:
    value = analysis.get(metric, 0.0)
    return float(value) if isinstance(value, int | float) else 0.0


def _compare_metrics(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, dict[str, float]]:
    comparison = {}
    for metric in METRICS:
        baseline_value = _metric_value(baseline, metric)
        candidate_value = _metric_value(candidate, metric)
        comparison[metric] = {
            "baseline": baseline_value,
            "candidate": candidate_value,
            "delta": round(candidate_value - baseline_value, 12),
        }
    return comparison


def _interpret(metrics: dict[str, dict[str, float]]) -> str:
    error_delta = metrics["policy_only_boundary_error_rate"]["delta"]
    instability_delta = metrics["boundary_instability_rate"]["delta"]
    if error_delta <= -0.15 and instability_delta <= -0.15:
        return "patch_rescues_boundary_variable"
    if error_delta < 0 or instability_delta < 0:
        return "patch_partial_rescue"
    if error_delta > 0.05 or instability_delta > 0.05:
        return "patch_worsens_or_confuses_boundary"
    return "no_clear_effect"


def _family_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    baseline_families = baseline.get("family_summaries", {})
    candidate_families = candidate.get("family_summaries", {})
    family_names = sorted(set(baseline_families) | set(candidate_families))
    comparison = {}
    for family in family_names:
        metrics = _compare_metrics(
            baseline_families.get(family, {}),
            candidate_families.get(family, {}),
        )
        comparison[family] = {
            **metrics,
            "interpretation": _interpret(metrics),
        }
    return comparison


def compare_analyses(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    baseline_name: str = "abstract",
    candidate_name: str = "clarified",
) -> dict[str, Any]:
    overall = _compare_metrics(baseline, candidate)
    return {
        "baseline_name": baseline_name,
        "candidate_name": candidate_name,
        "baseline_n_cases": int(baseline.get("n_cases", 0) or 0),
        "candidate_n_cases": int(candidate.get("n_cases", 0) or 0),
        "baseline_n_rows": int(baseline.get("n_rows", 0) or 0),
        "candidate_n_rows": int(candidate.get("n_rows", 0) or 0),
        "overall": overall,
        "overall_interpretation": _interpret(overall),
        "family_comparison": _family_comparison(baseline, candidate),
    }


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline-name", default="abstract")
    parser.add_argument("--candidate-name", default="clarified")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    result = compare_analyses(
        baseline=_load_json(args.baseline),
        candidate=_load_json(args.candidate),
        baseline_name=args.baseline_name,
        candidate_name=args.candidate_name,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
