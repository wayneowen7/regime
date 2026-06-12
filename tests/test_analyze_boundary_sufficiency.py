import json
from pathlib import Path
import tempfile
import unittest

from regime_pilot.analyze_boundary_sufficiency import analyze_runs, main


def row(
    case_id,
    condition,
    expected_family,
    model_family,
    policy_adherence,
    expected_decision=None,
    model_decision=None,
    invalid_used=0,
    stale_matches=0,
):
    return {
        "case_id": case_id,
        "condition": condition,
        "expected_decision": expected_decision or "remove",
        "model_decision": model_decision or "remove",
        "expected_decision_family": expected_family,
        "model_decision_family": model_family,
        "policy_adherence": policy_adherence,
        "invalid_used_precedent_count": invalid_used,
        "stale_rationale_match_count": stale_matches,
    }


def run_result(model, rows_by_condition):
    return {
        "model": model,
        "memory_view": "operational",
        "policy_view": "brief",
        "stale_warning": False,
        "conditions": list(rows_by_condition.keys()),
        "rows": rows_by_condition,
        "summaries": {},
    }


class AnalyzeBoundarySufficiencyTests(unittest.TestCase):
    def test_empty_input_returns_zero_rates_and_no_candidates(self):
        result = analyze_runs([])

        self.assertEqual(result["n_cases"], 0)
        self.assertEqual(result["policy_only_boundary_error_rate"], 0.0)
        self.assertEqual(result["current_guidance_rescue_rate"], 0.0)
        self.assertEqual(result["stale_guidance_harm_rate"], 0.0)
        self.assertEqual(result["boundary_instability_rate"], 0.0)
        self.assertEqual(result["invalid_used_precedent_rate"], 0.0)
        self.assertEqual(result["pseudo_consensus_candidates"], [])
        self.assertEqual(result["per_case"], {})

    def test_single_run_computes_rescue_harm_invalid_and_stale_triage(self):
        result = analyze_runs(
            [
                run_result(
                    "model-a",
                    {
                        "policy_only": [
                            row("C1", "policy_only", "intervention", "non_removal", False),
                            row("C2", "policy_only", "non_removal", "non_removal", True),
                        ],
                        "regime_aware": [
                            row("C1", "regime_aware", "intervention", "intervention", True),
                            row("C2", "regime_aware", "non_removal", "non_removal", True),
                        ],
                        "naive_memory": [
                            row(
                                "C1",
                                "naive_memory",
                                "intervention",
                                "intervention",
                                True,
                                stale_matches=1,
                            ),
                            row(
                                "C2",
                                "naive_memory",
                                "non_removal",
                                "intervention",
                                False,
                                invalid_used=1,
                                stale_matches=1,
                            ),
                        ],
                    },
                )
            ]
        )

        self.assertEqual(result["n_cases"], 2)
        self.assertEqual(result["policy_only_boundary_error_rate"], 0.5)
        self.assertEqual(result["current_guidance_rescue_rate"], 1.0)
        self.assertEqual(result["stale_guidance_harm_rate"], 1.0)
        self.assertEqual(result["invalid_used_precedent_rate"], 1 / 6)
        self.assertEqual(result["stale_rationale_match_total"], 2)
        self.assertEqual(result["per_case"]["C1"]["policy_only_correct"], False)
        self.assertEqual(result["per_case"]["C1"]["regime_aware_correct"], True)
        self.assertEqual(result["per_case"]["C2"]["naive_memory_correct"], False)

    def test_multi_run_computes_instability_pseudo_consensus_and_cli_output(self):
        runs = [
            run_result(
                "model-a",
                {
                    "policy_only": [
                        row("C3", "policy_only", "intervention", "intervention", True),
                        row("C4", "policy_only", "intervention", "intervention", True),
                    ],
                    "naive_memory": [
                        row("C3", "naive_memory", "intervention", "non_removal", False),
                        row("C4", "naive_memory", "intervention", "intervention", True),
                    ],
                },
            ),
            run_result(
                "model-b",
                {
                    "regime_aware": [
                        row("C3", "regime_aware", "intervention", "non_removal", False),
                        row("C4", "regime_aware", "intervention", "intervention", True),
                    ]
                },
            ),
        ]

        result = analyze_runs(runs)

        self.assertEqual(result["boundary_instability_rate"], 0.5)
        self.assertEqual(result["pseudo_consensus_candidates"], ["C3"])
        self.assertEqual(result["per_case"]["C3"]["decision_families"], ["intervention", "non_removal"])
        self.assertEqual(result["per_case"]["C4"]["decision_families"], ["intervention"])

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "run.json"
            output_path = Path(tmp) / "analysis.json"
            input_path.write_text(json.dumps(runs[0]), encoding="utf-8")

            main(["--inputs", str(input_path), "--output", str(output_path)])

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["n_cases"], 2)
            self.assertIn("per_case", written)

    def test_cli_loads_case_metadata_and_groups_by_boundary_family(self):
        runs = [
            run_result(
                "model-a",
                {
                    "policy_only": [
                        row("C5", "policy_only", "intervention", "non_removal", False),
                        row("C6", "policy_only", "non_removal", "non_removal", True),
                    ],
                    "regime_aware": [
                        row("C5", "regime_aware", "intervention", "intervention", True),
                        row("C6", "regime_aware", "non_removal", "non_removal", True),
                    ],
                },
            )
        ]

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "run.json"
            cases_path = Path(tmp) / "cases.jsonl"
            output_path = Path(tmp) / "analysis.json"
            input_path.write_text(json.dumps(runs[0]), encoding="utf-8")
            cases_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "case_id": "C5",
                                "expected_rationale": (
                                    "boundary_family=future_reform_vs_current_voting_instruction; "
                                    "hidden_anchor_label=current_instruction"
                                ),
                            }
                        ),
                        json.dumps(
                            {
                                "case_id": "C6",
                                "expected_rationale": (
                                    "boundary_family=obvious_satire_vs_deceptive_notice; "
                                    "hidden_anchor_label=obvious_satire"
                                ),
                            }
                        ),
                    ]
                ),
                encoding="utf-8",
            )

            main(
                [
                    "--inputs",
                    str(input_path),
                    "--cases",
                    str(cases_path),
                    "--output",
                    str(output_path),
                ]
            )

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                written["per_case"]["C5"]["boundary_family"],
                "future_reform_vs_current_voting_instruction",
            )
            self.assertEqual(
                written["per_case"]["C6"]["hidden_anchor_label"],
                "obvious_satire",
            )
            self.assertEqual(
                written["family_summaries"]["future_reform_vs_current_voting_instruction"][
                    "current_guidance_rescue_rate"
                ],
                1.0,
            )

    def test_action_granularity_metrics_separate_family_and_exact_action_errors(self):
        result = analyze_runs(
            [
                run_result(
                    "model-a",
                    {
                        "policy_only": [
                            row(
                                "A1",
                                "policy_only",
                                "non_removal",
                                "non_removal",
                                False,
                                expected_decision="contextualize",
                                model_decision="allow",
                            ),
                            row(
                                "A2",
                                "policy_only",
                                "intervention",
                                "intervention",
                                False,
                                expected_decision="remove",
                                model_decision="escalate",
                            ),
                            row(
                                "A3",
                                "policy_only",
                                "intervention",
                                "non_removal",
                                False,
                                expected_decision="remove",
                                model_decision="contextualize",
                            ),
                        ],
                        "regime_aware": [
                            row(
                                "A1",
                                "regime_aware",
                                "non_removal",
                                "non_removal",
                                True,
                                expected_decision="contextualize",
                                model_decision="contextualize",
                            ),
                            row(
                                "A2",
                                "regime_aware",
                                "intervention",
                                "intervention",
                                True,
                                expected_decision="remove",
                                model_decision="remove",
                            ),
                            row(
                                "A3",
                                "regime_aware",
                                "intervention",
                                "intervention",
                                True,
                                expected_decision="remove",
                                model_decision="remove",
                            ),
                        ],
                    },
                )
            ]
        )

        self.assertEqual(result["policy_only_exact_action_error_rate"], 1.0)
        self.assertEqual(result["policy_only_decision_family_error_rate"], 1 / 3)
        self.assertEqual(result["policy_only_action_granularity_error_rate"], 2 / 3)
        self.assertEqual(result["action_granularity_rescue_rate"], 1.0)
        self.assertEqual(result["per_case"]["A1"]["policy_only_exact_correct"], False)
        self.assertEqual(result["per_case"]["A1"]["policy_only_family_correct"], True)


if __name__ == "__main__":
    unittest.main()
