# POLAR-Active Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first runnable POLAR-Active loop that localizes policy-to-operation gaps from existing LLM results, proposes structured IR patches, compiles a patched operational policy, and evaluates it against existing action-granularity baselines.

**Architecture:** Add a focused `regime_pilot.polar_active` module that reuses existing case schema, result JSON shape, and POLAR-Compact compiler conventions. The v1 loop is deterministic and artifact-first: raw LLM outputs stay in existing result files, while generated gap reports, patches, compiled policies, and text-free summaries become reproducible artifacts.

**Tech Stack:** Python stdlib, existing `regime_pilot` modules, `unittest`, existing Ollama runner for remote evaluation.

---

### File Structure

- Create: `pilot/src/regime_pilot/polar_active.py`
  - Owns result loading, gap localization, patch proposal, patch application, compiled policy rendering, text-free summaries, and CLI.
- Create: `tests/test_polar_active.py`
  - Covers RED/GREEN tests for gap localization, patch proposal, compilation, length control, and text-free output.
- Create: `pilot/results/polar_active_action_granularity_gap_report.json`
  - Text-free gap report generated from existing action-granularity/POLAR-Compact result files.
- Create: `pilot/data/polar_active_policies_action_granularity.json`
  - Compiled operational policy for the action-granularity pilot.
- Create: `pilot/data/polar_active_sidecar_action_granularity.json`
  - Sidecar with gap ids, patch ids, affected case ids, and selected cues.
- Create: `pilot/results/polar_active_action_granularity_summary.json`
  - Text-free artifact summary before remote LLM evaluation.
- Modify: `docs/research_notes/2026-06-12-polar-compact-followup-and-rewrite-baseline.md`
  - Append a short POLAR-Active implementation status section after results are generated.

### Task 1: Add Failing Unit Tests for Gap Localization

**Files:**
- Create: `tests/test_polar_active.py`
- Create later: `pilot/src/regime_pilot/polar_active.py`

- [ ] **Step 1: Write failing tests**

```python
import unittest

from regime_pilot.polar_active import (
    localize_gaps_from_rows,
    parse_case_metadata,
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
        self.assertEqual(gaps[0].harm_direction, "under_enforcement")
        self.assertEqual(gaps[1].harm_direction, "wrong_action_granularity")
        self.assertEqual(gaps[0].candidate_cues, ["official_format", "weak_parody_label"])
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_polar_active -v
```

Expected: fail with `ModuleNotFoundError` or missing function import.

### Task 2: Implement Gap Localization

**Files:**
- Create: `pilot/src/regime_pilot/polar_active.py`
- Test: `tests/test_polar_active.py`

- [ ] **Step 1: Implement dataclasses and localizer**

Implement:

```python
@dataclass(frozen=True)
class GapReport:
    gap_id: str
    rule_id: str
    boundary_family: str
    action_contrast: str
    gap_type: str
    error_pairs: list[str]
    affected_case_ids: list[str]
    candidate_cues: list[str]
    harm_direction: str
    confidence: float
```

Also implement:

- `parse_case_metadata(case)`
- `decision_severity(decision)`
- `classify_gap(row)`
- `localize_gaps_from_rows(rows, cases, policy_condition)`

The localizer must group by `(rule_id, boundary_family, action_contrast, gap_type, error_pair)` and produce deterministic ids such as `gap-0001`.

- [ ] **Step 2: Run tests and verify GREEN**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_polar_active -v
```

Expected: `OK`.

### Task 3: Add Failing Tests for Patch Proposal and Compilation

**Files:**
- Modify: `tests/test_polar_active.py`

- [ ] **Step 1: Add tests**

```python
from regime_pilot.polar_active import (
    apply_patches_to_policies,
    compile_polar_active_artifacts,
    propose_patches,
)


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
        patches = propose_patches(
            localize_gaps_from_rows(
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
        )

        compiled, sidecar = apply_patches_to_policies(policies, patches, length_budget_chars=450)

        rule_text = compiled["regime"]["rules"]["satire"]
        self.assertIn("POLAR-Active patches:", rule_text)
        self.assertIn("official_format", rule_text)
        self.assertNotIn("raw case text", rule_text)
        self.assertLessEqual(len(rule_text), 450)
        self.assertEqual(sidecar["patch_count"], 1)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_polar_active -v
```

Expected: fail because patch functions do not exist.

### Task 4: Implement Patch Proposal, Compiler, and CLI

**Files:**
- Modify: `pilot/src/regime_pilot/polar_active.py`
- Test: `tests/test_polar_active.py`

- [ ] **Step 1: Implement patch dataclass and functions**

Implement:

- `IRPatch`
- `propose_patches(gaps, max_patches=8, max_cues_per_patch=5)`
- `apply_patches_to_policies(policies, patches, length_budget_chars=1200)`
- `compile_polar_active_artifacts(...)`
- CLI accepting:
  - `--policies`
  - `--cases`
  - `--results`
  - `--policy-condition`
  - `--output-policies`
  - `--output-sidecar`
  - `--output-gap-report`
  - `--output-summary`
  - `--max-patches`
  - `--length-budget-chars`

- [ ] **Step 2: Run unit tests**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.test_polar_active -v
```

Expected: `OK`.

### Task 5: Generate Local POLAR-Active Artifacts

**Files:**
- Create: `pilot/data/polar_active_policies_action_granularity.json`
- Create: `pilot/data/polar_active_sidecar_action_granularity.json`
- Create: `pilot/results/polar_active_action_granularity_gap_report.json`
- Create: `pilot/results/polar_active_action_granularity_summary.json`

- [ ] **Step 1: Run CLI on existing POLAR-Compact result files**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m regime_pilot.polar_active `
  --policies pilot/data/polar_compact_policies_action_granularity.json `
  --cases pilot/data/action_granularity_cases.jsonl `
  --results pilot/results/remote_20260612_polar_compact_qwen25_7b_polar_compact_12case_full_on.json pilot/results/remote_20260612_polar_compact_llama32_polar_compact_12case_full_on.json `
  --policy-condition policy_only `
  --output-policies pilot/data/polar_active_policies_action_granularity.json `
  --output-sidecar pilot/data/polar_active_sidecar_action_granularity.json `
  --output-gap-report pilot/results/polar_active_action_granularity_gap_report.json `
  --output-summary pilot/results/polar_active_action_granularity_summary.json `
  --max-patches 8 `
  --length-budget-chars 1200
```

Expected: writes all four artifacts and summary has `contains_raw_text=false`.

- [ ] **Step 2: Inspect artifact summaries**

Run:

```powershell
Get-Content -Raw pilot/results/polar_active_action_granularity_summary.json
```

Expected: includes `gap_count`, `patch_count`, `patched_rule_count`, and prompt length statistics.

### Task 6: Verify and Commit Local Implementation

**Files:**
- All files above.

- [ ] **Step 1: Run full test suite**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Check text-free summaries**

Run:

```powershell
Select-String -Path pilot/results/polar_active_action_granularity_summary.json,pilot/results/polar_active_action_granularity_gap_report.json,pilot/data/polar_active_sidecar_action_granularity.json -Pattern 'raw case text must not appear','OFFICIAL NOTICE','sample transcript','violating transcript' -SimpleMatch
```

Expected: no matches.

- [ ] **Step 3: Stage and commit**

Run:

```powershell
git add pilot/src/regime_pilot/polar_active.py tests/test_polar_active.py pilot/data/polar_active_policies_action_granularity.json pilot/data/polar_active_sidecar_action_granularity.json pilot/results/polar_active_action_granularity_gap_report.json pilot/results/polar_active_action_granularity_summary.json docs/superpowers/plans/2026-06-17-polar-active-implementation-plan.md
git commit -m "Implement POLAR-Active compiler loop"
```

### Task 7: Remote Evaluation

**Files:**
- Create raw remote outputs under ignored `data/raw/` if needed.
- Create text-free summary under `pilot/results/`.

- [ ] **Step 1: Sync code and artifacts to remote**

Use `scp`/`tar` to copy `pilot/`, `tests/`, `scripts/`, and needed docs to `lenovo@10.147.18.151`.

- [ ] **Step 2: Run qwen2.5:7b and llama3.2 on POLAR-Active policy**

Run the existing `regime_pilot.run_llm_pilot` with:

- policies: `pilot/data/polar_active_policies_action_granularity.json`
- cases: `pilot/data/action_granularity_cases.jsonl`
- precedents: `pilot/data/action_granularity_guidance_action.jsonl`
- conditions: `policy_only`
- memory_view: `operational`
- policy_view: `full`
- stale_warning: `on`

- [ ] **Step 3: Copy raw outputs back and compare**

Generate a text-free comparison against:

- `action_rubric`
- `polar_compact`
- `rewrite_length_matched`

- [ ] **Step 4: Update research note and commit**

Append a short status section to `docs/research_notes/2026-06-12-polar-compact-followup-and-rewrite-baseline.md` with whether POLAR-Active improved exact-action, family error, instability, and prompt length.
