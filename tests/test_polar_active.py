import unittest

from regime_pilot.polar_active import (
    IRPatch,
    apply_patches_to_policies,
    compile_single_patch_policy_collection,
    localize_gaps_from_rows,
    parse_case_metadata,
    propose_patches,
    verify_patch_candidates,
)


class PolarActiveTests(unittest.TestCase):
    def test_parse_case_metadata_extracts_boundary_variables(self):
        case = {
            "case_id": "AG-T-007",
            "expected_decision": "remove",
            "expected_rationale": (
                "boundary_family=obvious_satire_vs_deceptive_notice; "
                "action_contrast=contextualize_vs_remove; "
                "boundary_variables=official_looking_format|current_cancellation|weak_parody_label"
            ),
        }

        metadata = parse_case_metadata(case)

        self.assertEqual(metadata["boundary_family"], "obvious_satire_vs_deceptive_notice")
        self.assertEqual(metadata["action_contrast"], "contextualize_vs_remove")
        self.assertEqual(
            metadata["boundary_variables"],
            ["official_looking_format", "current_cancellation", "weak_parody_label"],
        )

    def test_localize_gaps_separates_boundary_and_action_errors(self):
        cases = [
            {
                "case_id": "c1",
                "policy_rule": "satire",
                "expected_decision": "remove",
                "expected_rationale": (
                    "boundary_family=satire; action_contrast=allow_vs_remove; "
                    "boundary_variables=official_format|weak_parody_label"
                ),
            },
            {
                "case_id": "c2",
                "policy_rule": "ballot_validity",
                "expected_decision": "contextualize",
                "expected_rationale": (
                    "boundary_family=education; action_contrast=allow_vs_contextualize; "
                    "boundary_variables=quote|official_source"
                ),
            },
        ]
        rows = [
            {
                "case_id": "c1",
                "model": "qwen2.5:7b",
                "policy_condition": "polar_compact",
                "expected_decision": "remove",
                "model_decision": "allow",
                "expected_decision_family": "intervention",
                "model_decision_family": "non_removal",
                "policy_adherence": False,
                "decision_family_adherence": False,
            },
            {
                "case_id": "c2",
                "model": "qwen2.5:7b",
                "policy_condition": "polar_compact",
                "expected_decision": "contextualize",
                "model_decision": "remove",
                "expected_decision_family": "intervention",
                "model_decision_family": "intervention",
                "policy_adherence": False,
                "decision_family_adherence": True,
            },
        ]

        gaps = localize_gaps_from_rows(rows, cases, policy_condition="polar_compact")

        self.assertEqual([gap.gap_type for gap in gaps], ["missing_boundary", "missing_action_edge"])
        self.assertEqual(gaps[0].regime_id, "unknown")
        self.assertEqual(gaps[0].harm_direction, "under_enforcement")
        self.assertEqual(gaps[1].harm_direction, "wrong_action_granularity")
        self.assertEqual(gaps[0].candidate_cues, ["official_format", "weak_parody_label"])

    def test_propose_patches_turns_gaps_into_structured_ir_patches(self):
        gaps = localize_gaps_from_rows(
            rows=[
                {
                    "case_id": "c1",
                    "model": "qwen2.5:7b",
                    "policy_condition": "polar_compact",
                    "expected_decision": "remove",
                    "model_decision": "allow",
                    "expected_decision_family": "intervention",
                    "model_decision_family": "non_removal",
                    "policy_adherence": False,
                    "decision_family_adherence": False,
                }
            ],
            cases=[
                {
                    "case_id": "c1",
                    "policy_rule": "satire",
                    "expected_decision": "remove",
                    "expected_rationale": (
                        "boundary_family=satire; action_contrast=allow_vs_remove; "
                        "boundary_variables=official_format|current_disruption|weak_parody_label"
                    ),
                }
            ],
            policy_condition="polar_compact",
        )

        patches = propose_patches(gaps, max_patches=1)

        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].patch_type, "add_boundary_variable")
        self.assertEqual(patches[0].regime_id, "unknown")
        self.assertEqual(patches[0].rule_id, "satire")
        self.assertEqual(patches[0].affected_case_ids, ["c1"])
        self.assertIn("official_format", patches[0].selected_cues)

    def test_apply_patches_adds_polar_active_section_without_case_text(self):
        policies = {
            "regime": {
                "name": "Example",
                "description": "Example policy",
                "rules": {
                    "satire": "Boundary: existing rule\nAction rubric:\n- allow: harmless satire"
                },
            }
        }
        gaps = localize_gaps_from_rows(
            rows=[
                {
                    "case_id": "c1",
                    "model": "qwen2.5:7b",
                    "policy_condition": "polar_compact",
                    "expected_decision": "remove",
                    "model_decision": "allow",
                    "expected_decision_family": "intervention",
                    "model_decision_family": "non_removal",
                    "policy_adherence": False,
                    "decision_family_adherence": False,
                }
            ],
            cases=[
                {
                    "case_id": "c1",
                    "active_regime_id": "regime",
                    "policy_rule": "satire",
                    "expected_decision": "remove",
                    "post": "raw case text must not appear",
                    "expected_rationale": (
                        "boundary_family=satire; action_contrast=allow_vs_remove; "
                        "boundary_variables=official_format|current_disruption"
                    ),
                }
            ],
            policy_condition="polar_compact",
        )
        patches = propose_patches(gaps)

        compiled, sidecar = apply_patches_to_policies(
            policies,
            patches,
            length_budget_chars=450,
        )

        rule_text = compiled["regime"]["rules"]["satire"]
        self.assertIn("POLAR-Active patches:", rule_text)
        self.assertIn("official_format", rule_text)
        self.assertNotIn("raw case text", rule_text)
        self.assertLessEqual(len(rule_text), 450)
        self.assertEqual(sidecar["patch_count"], 1)
        self.assertEqual(sidecar["applied_patch_count"], 1)

    def test_apply_patches_only_modifies_matching_regime(self):
        policies = {
            "normal": {
                "name": "Normal",
                "description": "Normal policy",
                "rules": {"satire": "Normal satire rule"},
            },
            "election": {
                "name": "Election",
                "description": "Election policy",
                "rules": {"satire": "Election satire rule"},
            },
        }
        gaps = localize_gaps_from_rows(
            rows=[
                {
                    "case_id": "c1",
                    "policy_condition": "polar_compact",
                    "expected_decision": "remove",
                    "model_decision": "allow",
                    "expected_decision_family": "intervention",
                    "model_decision_family": "non_removal",
                    "policy_adherence": False,
                    "decision_family_adherence": False,
                }
            ],
            cases=[
                {
                    "case_id": "c1",
                    "active_regime_id": "election",
                    "policy_rule": "satire",
                    "expected_rationale": (
                        "boundary_family=satire; action_contrast=allow_vs_remove; "
                        "boundary_variables=official_format|current_disruption"
                    ),
                }
            ],
            policy_condition="polar_compact",
        )

        compiled, sidecar = apply_patches_to_policies(policies, propose_patches(gaps))

        self.assertNotIn("POLAR-Active patches:", compiled["normal"]["rules"]["satire"])
        self.assertIn("POLAR-Active patches:", compiled["election"]["rules"]["satire"])
        self.assertEqual(sidecar["patched_rule_count"], 1)

    def test_verify_patch_candidates_accepts_rescue_without_no_harm_violation(self):
        patches = [
            IRPatch(
                patch_id="patch-0001",
                gap_id="gap-0001",
                regime_id="election",
                patch_type="add_boundary_variable",
                rule_id="satire",
                boundary_family="satire",
                action_contrast="allow_vs_contextualize",
                affected_case_ids=["c1"],
                selected_cues=["parody_label"],
                target_error_pairs=["contextualize->remove"],
                instruction="choose contextualize over remove",
                expected_effect="rescue c1",
            ),
            IRPatch(
                patch_id="patch-0002",
                gap_id="gap-0002",
                regime_id="election",
                patch_type="add_action_edge",
                rule_id="satire",
                boundary_family="satire",
                action_contrast="remove_vs_escalate",
                affected_case_ids=["c2"],
                selected_cues=["coordination"],
                target_error_pairs=["escalate->remove"],
                instruction="choose escalate over remove",
                expected_effect="rescue c2",
            ),
        ]
        baseline = {
            "policy_only_exact_action_error_rate": 0.50,
            "policy_only_decision_family_error_rate": 0.25,
            "boundary_instability_rate": 0.25,
            "per_case": {
                "c1": {"policy_only_exact_correct": False},
                "c2": {"policy_only_exact_correct": False},
            },
        }
        candidate_analyses = {
            "patch-0001": {
                "policy_only_exact_action_error_rate": 0.50,
                "policy_only_decision_family_error_rate": 0.25,
                "boundary_instability_rate": 0.25,
                "per_case": {
                    "c1": {"policy_only_exact_correct": True},
                    "c2": {"policy_only_exact_correct": False},
                },
            },
            "patch-0002": {
                "policy_only_exact_action_error_rate": 0.75,
                "policy_only_decision_family_error_rate": 0.25,
                "boundary_instability_rate": 0.25,
                "per_case": {
                    "c1": {"policy_only_exact_correct": False},
                    "c2": {"policy_only_exact_correct": True},
                },
            },
        }

        summary = verify_patch_candidates(patches, baseline, candidate_analyses)

        self.assertEqual(summary["accepted_patch_ids"], ["patch-0001"])
        self.assertEqual(summary["rejected_patch_ids"], ["patch-0002"])
        decisions = {item["patch_id"]: item for item in summary["patch_decisions"]}
        self.assertTrue(decisions["patch-0001"]["accepted"])
        self.assertEqual(decisions["patch-0001"]["target_rescue_count"], 1)
        self.assertFalse(decisions["patch-0002"]["accepted"])
        self.assertIn("exact_error_harm", decisions["patch-0002"]["rejection_reasons"])

    def test_compile_single_patch_policy_collection_outputs_one_policy_per_patch(self):
        policies = {
            "election": {
                "name": "Election",
                "description": "Election policy",
                "rules": {
                    "satire": "Satire rule",
                    "counting": "Counting rule",
                },
            }
        }
        patches = [
            IRPatch(
                patch_id="patch-0001",
                gap_id="gap-0001",
                regime_id="election",
                patch_type="add_boundary_variable",
                rule_id="satire",
                boundary_family="satire",
                action_contrast="allow_vs_contextualize",
                affected_case_ids=["c1"],
                selected_cues=["parody_label"],
                target_error_pairs=["contextualize->remove"],
                instruction="choose contextualize over remove",
                expected_effect="rescue c1",
            ),
            IRPatch(
                patch_id="patch-0002",
                gap_id="gap-0002",
                regime_id="election",
                patch_type="add_action_edge",
                rule_id="counting",
                boundary_family="counting",
                action_contrast="remove_vs_escalate",
                affected_case_ids=["c2"],
                selected_cues=["coordination"],
                target_error_pairs=["escalate->remove"],
                instruction="choose escalate over remove",
                expected_effect="rescue c2",
            ),
        ]

        collection = compile_single_patch_policy_collection(policies, patches)

        self.assertEqual(sorted(collection), ["patch-0001", "patch-0002"])
        patch_1_policy = collection["patch-0001"]["policies"]
        patch_2_policy = collection["patch-0002"]["policies"]
        self.assertIn("patch-0001", patch_1_policy["election"]["rules"]["satire"])
        self.assertNotIn("patch-0002", patch_1_policy["election"]["rules"]["counting"])
        self.assertIn("patch-0002", patch_2_policy["election"]["rules"]["counting"])
        self.assertEqual(collection["patch-0001"]["sidecar"]["patch_count"], 1)


if __name__ == "__main__":
    unittest.main()
