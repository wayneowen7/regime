from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any


def _normalized_label(value: Any) -> str:
    return str(value or "").strip().lower()


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_anchor_reviews(path: str) -> list[dict[str, Any]]:
    reviews = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                reviews.append(json.loads(stripped))
    return reviews


def _judge_labels_by_candidate(judge_results: list[dict[str, Any]]) -> dict[str, list[str]]:
    labels_by_candidate: dict[str, list[str]] = defaultdict(list)
    for result in judge_results:
        if result.get("parse_error"):
            continue
        label = _normalized_label(result.get("label"))
        if label:
            labels_by_candidate[str(result.get("candidate_id", ""))].append(label)
    return labels_by_candidate


def _unanimous_label(labels: list[str]) -> str | None:
    if len(labels) >= 2 and len(set(labels)) == 1:
        return labels[0]
    return None


def analyze_anchor_review(
    barred_like_result: dict[str, Any],
    anchor_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = {
        str(candidate.get("candidate_id", "")): candidate
        for candidate in barred_like_result.get("generated_candidates", [])
        if candidate.get("candidate_id")
    }
    reviews = {
        str(review.get("candidate_id", "")): review
        for review in anchor_reviews
        if review.get("candidate_id")
    }
    labels_by_candidate = _judge_labels_by_candidate(
        barred_like_result.get("judge_results", [])
    )
    original_manual_review_ids = {
        str(item.get("candidate_id", ""))
        for item in barred_like_result.get("manual_review_candidates", [])
        if item.get("candidate_id")
    }

    per_candidate: dict[str, dict[str, Any]] = {}
    reviewed_count = 0
    anchor_agreements = 0
    anchor_comparable_count = 0
    pseudo_consensus_ids = []
    family_drift_count = 0
    manual_review_resolved_count = 0

    for candidate_id in sorted(candidates):
        candidate = candidates[candidate_id]
        review = reviews.get(candidate_id, {})
        anchor_label = _normalized_label(review.get("anchor_label"))
        review_status = str(review.get("review_status", "")).strip().lower()
        judge_labels = labels_by_candidate.get(candidate_id, [])
        unanimous_label = _unanimous_label(judge_labels)
        family_drift = review_status == "family_drift"
        pseudo_consensus = (
            bool(anchor_label)
            and unanimous_label is not None
            and unanimous_label != anchor_label
        )

        if anchor_label:
            reviewed_count += 1
            if unanimous_label is not None:
                anchor_comparable_count += 1
                if unanimous_label == anchor_label:
                    anchor_agreements += 1
            if candidate_id in original_manual_review_ids:
                manual_review_resolved_count += 1
        if family_drift:
            family_drift_count += 1
        if pseudo_consensus:
            pseudo_consensus_ids.append(candidate_id)

        per_candidate[candidate_id] = {
            "candidate_id": candidate_id,
            "family": str(candidate.get("family", "")),
            "content": str(candidate.get("content", "")),
            "proposed_label": _normalized_label(candidate.get("proposed_label")),
            "anchor_label": anchor_label,
            "anchor_rationale": str(review.get("anchor_rationale", "")),
            "review_status": review_status,
            "judge_labels": judge_labels,
            "unanimous_judge_label": unanimous_label,
            "anchor_agrees": (
                unanimous_label == anchor_label
                if anchor_label and unanimous_label
                else False
            ),
            "pseudo_consensus": pseudo_consensus,
            "family_drift": family_drift,
        }

    return {
        "n_reviewed": reviewed_count,
        "anchor_agreement_rate": _rate(anchor_agreements, anchor_comparable_count),
        "pseudo_consensus_candidates": pseudo_consensus_ids,
        "family_drift_count": family_drift_count,
        "manual_review_resolved_count": manual_review_resolved_count,
        "per_candidate": per_candidate,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    analysis = analyze_anchor_review(
        barred_like_result=_load_json(args.result),
        anchor_reviews=load_anchor_reviews(args.review),
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
