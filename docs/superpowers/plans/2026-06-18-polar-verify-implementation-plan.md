# POLAR-Verify Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a verifier/no-harm gate on top of POLAR-Active so atomic patches are accepted only when they rescue target probes without worsening global or neighboring metrics.

**Architecture:** Extend `IRPatch` with `affected_case_ids`, compile single-patch candidate policies, and add a deterministic verifier that compares baseline analysis JSON against per-patch candidate analysis JSON. The verifier writes text-free acceptance artifacts so remote LLM outputs can stay under `data/raw/`.

**Tech Stack:** Python stdlib, `unittest`, existing `regime_pilot.analyze_boundary_sufficiency` analysis schema, existing `run_llm_pilot.py` remote runner.

---

### Task 1: Patch Provenance

**Files:**
- Modify: `pilot/src/regime_pilot/polar_active.py`
- Modify: `tests/test_polar_active.py`

- [x] **Step 1: Write failing test**

Add assertions that `propose_patches()` carries `affected_case_ids` from `GapReport` into each `IRPatch`.

- [x] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest tests.test_polar_active -v
```

Expected: fails because `IRPatch` has no `affected_case_ids`.

- [x] **Step 3: Implement minimal provenance field**

Add `affected_case_ids: list[str]` to `IRPatch` and fill it in `propose_patches()`.

- [x] **Step 4: Verify green**

Run the same targeted test command and expect pass.

### Task 2: Verifier API

**Files:**
- Modify: `pilot/src/regime_pilot/polar_active.py`
- Modify: `tests/test_polar_active.py`

- [x] **Step 1: Write failing test**

Add a test that builds a baseline analysis and two candidate analyses:

- `patch-0001` rescues its target and does not worsen aggregate metrics, so it is accepted.
- `patch-0002` rescues nothing or raises exact-action error, so it is rejected.

- [x] **Step 2: Run test to verify failure**

Run targeted tests. Expected failure: verifier function does not exist.

- [x] **Step 3: Implement verifier**

Add:

```python
def verify_patch_candidates(
    patches: list[IRPatch],
    baseline_analysis: dict[str, Any],
    candidate_analyses: dict[str, dict[str, Any]],
    max_exact_error_delta: float = 0.0,
    max_family_error_delta: float = 0.0,
    max_instability_delta: float = 0.0,
) -> dict[str, Any]:
    ...
```

Each patch decision should include `accepted`, `target_rescue_count`, metric deltas, and rejection reasons.

- [x] **Step 4: Verify green**

Run targeted tests.

### Task 3: Candidate Policy Artifacts

**Files:**
- Modify: `pilot/src/regime_pilot/polar_active.py`
- Add generated files under `pilot/data/` and `pilot/results/`

- [x] **Step 1: Add helper for single-patch policy collection**

Add a function that compiles one policy file per patch. Each file should contain exactly one patch and a sidecar list mapping `patch_id -> policy_path`.

- [x] **Step 2: Generate artifact**

Use current POLAR-Compact baseline results to generate candidate policy files for the 8 atomic patches.

- [x] **Step 3: Remote run**

Run `qwen2.5:7b` and `llama3.2:latest` on all candidate policies with `--limit-cases 12`.

- [x] **Step 4: Analyze and verify**

Produce per-patch analysis files and a verifier summary.

### Task 4: Documentation and Commit

**Files:**
- Add or modify: `docs/research_notes/2026-06-18-polar-verify-gated-repair.md`

- [x] **Step 1: Record method and result**

Write a Chinese memo explaining whether verifier selects any patches and what it implies.

- [x] **Step 2: Full verification**

Run full unittest, text leakage scan, and git ignore check.

- [ ] **Step 3: Commit and push**

Commit only relevant method/artifact/doc files and push the current branch.
