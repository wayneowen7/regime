import unittest

from regime_pilot.polar_active import (
    apply_patches_to_policies,
    localize_gaps_from_rows,
    parse_case_metadata,
    propose_patches,
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


if __name__ == "__main__":
    unittest.main()
