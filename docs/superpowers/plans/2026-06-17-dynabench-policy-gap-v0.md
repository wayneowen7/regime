# DynaBench Policy Gap V0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a DynaBench-only v0 benchmark that tests whether policy views progress from abstract intent to boundary clarification to action rubric.

**Architecture:** Use DynaBench because it satisfies the main-study invariant: natural-language policy text, transcript text, and ground-truth PASS/FAIL label. Generate runner-compatible artifacts under `data/raw/dynabench_policy_gap_v0/` because they contain third-party text; write only text-free summaries to `pilot/results/`.

**Tech Stack:** Python standard library, existing `regime_pilot` schema/LLM runner, unittest, Ollama smoke on the remote GPU when available.

---

### Task 1: Converter Unit Tests

**Files:**
- Create: `tests/test_dynabench_policy_gap.py`
- Create later: `pilot/src/regime_pilot/dynabench_policy_gap.py`

- [ ] **Step 1: Write the failing test**

Test that a tiny DynaBench-like sample produces:

```python
cases, policies, summary = build_dynabench_policy_gap_artifacts(records, sample_size=2)
assert len(cases) == 2
assert cases[0]["active_regime_id"] in policies["abstract"]
assert cases[0]["expected_decision"] in {"allow", "remove"}
assert cases[0]["post"] == "sample transcript"
assert policies["abstract"][cases[0]["active_regime_id"]]["rules"][cases[0]["policy_rule"]]
assert summary["contains_raw_text"] is False
```

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest tests.test_dynabench_policy_gap -v
```

Expected: fails with `ModuleNotFoundError` for `regime_pilot.dynabench_policy_gap`.

### Task 2: Converter Implementation

**Files:**
- Create: `pilot/src/regime_pilot/dynabench_policy_gap.py`

- [ ] **Step 1: Implement deterministic conversion**

Rules:

```text
PASS -> expected_decision = allow
FAIL -> expected_decision = remove
abstract policy -> generic compliance intent
boundary policy -> original DynaBench policy text
action rubric policy -> original policy plus explicit PASS/FAIL to allow/remove mapping
```

- [ ] **Step 2: Write artifacts**

Output paths:

```text
data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_cases_v0.jsonl
data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_policies_abstract.json
data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_policies_boundary.json
data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_policies_action_rubric.json
data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_empty_precedents.jsonl
pilot/results/dynabench_policy_gap_v0_summary.json
```

- [ ] **Step 3: Verify green**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest tests.test_dynabench_policy_gap -v
```

Expected: tests pass.

### Task 3: Generate V0 Artifacts

**Files:**
- Raw output under `data/raw/dynabench_policy_gap_v0/`
- Summary output: `pilot/results/dynabench_policy_gap_v0_summary.json`

- [ ] **Step 1: Generate 100 cases**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m regime_pilot.dynabench_policy_gap --raw data/raw/dataset_bootstrap/dynabench_sample500.jsonl --sample-size 100
```

Expected summary:

```text
selected_count = 100
label_counts include PASS and FAIL
contains_raw_text = false
```

### Task 4: Smoke Run

**Files:**
- Output examples under `pilot/results/`

- [ ] **Step 1: Run local fake-client tests**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run one small model smoke if Ollama is reachable**

Use `run_llm_pilot.py` with `condition=policy_only`, `top_k=0`, and `limit_cases=10` for each policy view. Skip with a documented note if no Ollama endpoint is reachable.

### Task 5: Documentation And Commit

**Files:**
- Create: `docs/research_notes/2026-06-17-dynabench-policy-gap-v0.md`
- Commit code, tests, summaries, and docs. Do not commit raw data under `data/raw/`.

- [ ] **Step 1: Write a Chinese result note**

Record:

```text
why DynaBench is the v0 main dataset
how labels map to actions
what raw artifacts were generated
whether smoke ran
```

- [ ] **Step 2: Verify and commit**

Run full tests, verify raw outputs are ignored, then commit.
