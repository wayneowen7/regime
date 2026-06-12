import json
from pathlib import Path
import tempfile
import unittest

from regime_pilot.analyze_barred_like_anchor_review import analyze_anchor_review, main


def candidate(candidate_id, family, proposed_label="allow"):
    return {
        "candidate_id": candidate_id,
        "family": family,
        "content": f"content for {candidate_id}",
        "proposed_label": proposed_label,
    }


def judge(candidate_id, label, judge_index=0):
    return {
        "candidate_id": candidate_id,
        "judge_index": judge_index,
        "label": label,
        "rationale": f"{label} rationale",
    }


class AnalyzeBarredLikeAnchorReviewTests(unittest.TestCase):
    def test_anchor_conflict_is_pseudo_consensus_not_generator_mismatch(self):
        result = {
            "generated_candidates": [
                candidate("C1", "future_reform", proposed_label="restrict"),
                candidate("C2", "satire", proposed_label="restrict"),
            ],
            "judge_results": [
                judge("C1", "restrict", 0),
                judge("C1", "restrict", 1),
                judge("C2", "allow", 0),
                judge("C2", "allow", 1),
            ],
            "manual_review_candidates": [
                {"candidate_id": "C1"},
                {"candidate_id": "C2"},
            ],
        }
        reviews = [
            {
                "candidate_id": "C1",
                "family": "future_reform",
                "anchor_label": "contextualize",
                "review_status": "resolved",
            },
            {
                "candidate_id": "C2",
                "family": "satire",
                "anchor_label": "allow",
                "review_status": "resolved",
            },
        ]

        analysis = analyze_anchor_review(result, reviews)

        self.assertEqual(analysis["n_reviewed"], 2)
        self.assertEqual(analysis["anchor_agreement_rate"], 0.5)
        self.assertEqual(analysis["pseudo_consensus_candidates"], ["C1"])
        self.assertEqual(analysis["manual_review_resolved_count"], 2)
        self.assertTrue(analysis["per_candidate"]["C1"]["pseudo_consensus"])
        self.assertFalse(analysis["per_candidate"]["C2"]["pseudo_consensus"])

    def test_family_drift_is_counted_separately(self):
        result = {
            "generated_candidates": [
                candidate("C3", "prediction_opinion_vs_false_certification"),
            ],
            "judge_results": [
                judge("C3", "escalate", 0),
                judge("C3", "escalate", 1),
            ],
            "manual_review_candidates": [{"candidate_id": "C3"}],
        }
        reviews = [
            {
                "candidate_id": "C3",
                "family": "prediction_opinion_vs_false_certification",
                "anchor_label": "escalate",
                "review_status": "family_drift",
            }
        ]

        analysis = analyze_anchor_review(result, reviews)

        self.assertEqual(analysis["family_drift_count"], 1)
        self.assertEqual(analysis["pseudo_consensus_candidates"], [])
        self.assertTrue(analysis["per_candidate"]["C3"]["family_drift"])

    def test_cli_writes_output(self):
        result = {
            "generated_candidates": [candidate("C4", "education_quote")],
            "judge_results": [judge("C4", "allow", 0), judge("C4", "allow", 1)],
            "manual_review_candidates": [{"candidate_id": "C4"}],
        }
        review = {
            "candidate_id": "C4",
            "family": "education_quote",
            "anchor_label": "allow",
            "review_status": "resolved",
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            result_path = tmp_dir / "barred_like.json"
            review_path = tmp_dir / "review.jsonl"
            output_path = tmp_dir / "analysis.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            review_path.write_text(json.dumps(review) + "\n", encoding="utf-8")

            main(
                [
                    "--result",
                    str(result_path),
                    "--review",
                    str(review_path),
                    "--output",
                    str(output_path),
                ]
            )

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["n_reviewed"], 1)
            self.assertEqual(written["anchor_agreement_rate"], 1.0)
            self.assertEqual(written["per_candidate"]["C4"]["anchor_label"], "allow")


if __name__ == "__main__":
    unittest.main()
