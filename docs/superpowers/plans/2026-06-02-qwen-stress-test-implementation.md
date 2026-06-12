# Qwen Stress Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 qwen2.5:7b stress matrix，判断它没有被 stale precedent 带偏是因为模型鲁棒，还是因为当前 policy 和 prompt 设置过强。

**Architecture:** 不重写现有 pilot，只在 LLM prompt/rendering 层增加两个实验开关：`policy_view` 和 `stale_warning`。评估层增加一个轻量 stale rationale heuristic，用于捕捉模型没有显式列出 invalid precedent id、但 rationale 继承无效旧 precedent 的情况。实验输出仍使用现有 JSON runner。

**Tech Stack:** Python 3, stdlib `unittest`, JSON/JSONL, Ollama HTTP runner, PowerShell/SSH for remote GPU execution.

---

## 文件结构

- Modify: `pilot/src/regime_pilot/llm_pilot.py`
  - 增加 `POLICY_VIEWS = {"full", "brief"}`。
  - `build_agent_prompt` 增加 `policy_view` 和 `stale_warning` 参数。
  - brief policy view 只展示 policy name、description、active policy focus，不展示完整 rule text。
  - stale warning off 时，不显示 `may be stale` 和 `only if its rationale still fits`。
  - `evaluate_agent_output` 增加 stale rationale heuristic 字段。
- Modify: `pilot/src/regime_pilot/run_llm_pilot.py`
  - `run_llm_pilot` 增加 `policy_view` 和 `stale_warning` 参数。
  - CLI 增加 `--policy-view` 和 `--stale-warning`。
  - 输出 JSON 顶层记录这两个配置。
  - summary 增加 `mean_stale_rationale_matches`。
- Modify: `tests/test_llm_pilot.py`
  - 增加 prompt 开关测试。
  - 增加 stale rationale heuristic 测试。
- Modify: `tests/test_run_llm_pilot.py`
  - 增加 runner 透传和结果记录测试。
- Create: `docs/research_notes/2026-06-02-qwen-stress-test-run.md`
  - 中文记录本轮 stress matrix 的设计、命令、结果和解释。
- Modify: `docs/research_notes/2026-06-01-artifact-index.md`
  - 增加 stress test plan、run note、结果 JSON。

## Task 1: Prompt stress knobs

**Files:**

- Modify: `pilot/src/regime_pilot/llm_pilot.py`
- Modify: `tests/test_llm_pilot.py`

- [ ] **Step 1: Write failing prompt tests**

Add tests that call:

```python
build_agent_prompt(
    policy={
        "name": "Election Integrity Period",
        "description": "Heightened election integrity policy.",
        "rules": {"voting_procedure": "Remove false voting time claims."},
    },
    test_case=make_test_case(),
    selected=[],
    memory_view="operational",
    policy_view="brief",
    stale_warning=False,
)
```

Expected assertions:

- prompt contains `active_policy_focus: voting_procedure`
- prompt does not contain `Policy rules:`
- prompt does not contain `Remove false voting time claims.`
- prompt does not contain `may be stale`
- prompt does not contain `rationale still fits`

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_llm_pilot -v
```

Expected: FAIL because `build_agent_prompt` does not accept `policy_view` or `stale_warning`.

- [ ] **Step 3: Implement prompt knobs**

In `llm_pilot.py`:

- Add `POLICY_VIEWS = {"full", "brief"}`.
- Add `_format_policy_section(policy, test_case, memory_view, policy_view)`.
- Validate `policy_view`.
- In brief mode, omit full rule text and include `active_policy_focus`.
- In stale warning off mode, use only a neutral precedent instruction.

- [ ] **Step 4: Verify green**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_llm_pilot -v
```

Expected: PASS.

## Task 2: Stale rationale heuristic

**Files:**

- Modify: `pilot/src/regime_pilot/llm_pilot.py`
- Modify: `tests/test_llm_pilot.py`

- [ ] **Step 1: Write failing heuristic tests**

Add one test where the selected precedent is incompatible with the active regime and the output rationale reuses the precedent rationale:

```python
result = evaluate_agent_output(
    test_case=make_test_case(),
    selected=[RetrievalResult(make_precedent("R1-P-001", "normal_civic_discussion_v1", ["normal_civic_discussion_v1"]), 1.2)],
    output={
        "decision": "contextualize",
        "rationale": "Normal-period discussion receives context.",
        "used_precedents": [],
    },
)
```

Expected:

- `stale_rationale_match_count == 1`
- `stale_rationale_precedent_ids == ["R1-P-001"]`

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_llm_pilot -v
```

Expected: FAIL because stale rationale fields do not exist.

- [ ] **Step 3: Implement heuristic**

In `llm_pilot.py`:

- Add small stopword-filtered token overlap helper.
- Only compare against selected precedents that are incompatible with the active regime.
- Count a match when overlap with the output rationale is at least 3 content tokens.
- Add `stale_rationale_match_count` and `stale_rationale_precedent_ids` to each row.

- [ ] **Step 4: Verify green**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_llm_pilot -v
```

Expected: PASS.

## Task 3: Runner support

**Files:**

- Modify: `pilot/src/regime_pilot/run_llm_pilot.py`
- Modify: `tests/test_run_llm_pilot.py`

- [ ] **Step 1: Write failing runner test**

Add a test calling:

```python
run_llm_pilot(
    policies_path=policies_path,
    precedents_path=precedents_path,
    test_cases_path=test_cases_path,
    client=client,
    model="fake-model",
    conditions=["regime_aware"],
    top_k=3,
    limit_cases=1,
    memory_view="operational",
    policy_view="brief",
    stale_warning=False,
)
```

Expected:

- result contains `policy_view == "brief"`
- result contains `stale_warning is False`
- summary contains `mean_stale_rationale_matches`
- prompt does not contain full rule text
- prompt does not contain stale-warning phrases

- [ ] **Step 2: Verify red**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_run_llm_pilot -v
```

Expected: FAIL because runner does not accept those parameters.

- [ ] **Step 3: Implement runner support**

In `run_llm_pilot.py`:

- Import `POLICY_VIEWS`.
- Add parameters and pass them to `build_agent_prompt`.
- Add summary field `mean_stale_rationale_matches`.
- Add CLI options:
  - `--policy-view`, choices `brief/full`, default `full`
  - `--stale-warning`, choices `on/off`, default `on`
- Convert `args.stale_warning == "on"` to bool.

- [ ] **Step 4: Verify green and full suite**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python -m unittest tests.test_run_llm_pilot -v
$env:PYTHONPATH='pilot/src'; python -m unittest discover -s tests -v
```

Expected: PASS.

## Task 4: Remote qwen2.5 stress matrix

**Files:**

- Create result JSON under `pilot/results/`
- Create: `docs/research_notes/2026-06-02-qwen-stress-test-run.md`
- Modify: `docs/research_notes/2026-06-01-artifact-index.md`

- [ ] **Step 1: Sync to remote**

Upload `docs/`, `pilot/`, and `tests/` to:

```bash
/home/lenovo/code/regime_moderation_pilot
```

- [ ] **Step 2: Remote tests**

Run:

```bash
cd /home/lenovo/code/regime_moderation_pilot
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 3: Run qwen2.5 stress matrix**

Run four configurations with model `qwen2.5:7b`, 10 cases, top-k 3, conditions `policy_only,naive_memory,regime_aware`:

- `full_warning_on`
- `full_warning_off`
- `brief_warning_on`
- `brief_warning_off`

Outputs:

- `pilot/results/llm_qwen25_7b_stress_full_warning_on.json`
- `pilot/results/llm_qwen25_7b_stress_full_warning_off.json`
- `pilot/results/llm_qwen25_7b_stress_brief_warning_on.json`
- `pilot/results/llm_qwen25_7b_stress_brief_warning_off.json`

- [ ] **Step 4: Pull and summarize**

Pull JSON files to local and summarize:

- exact adherence
- family adherence
- invalid used precedents
- stale rationale matches
- parse errors

- [ ] **Step 5: Write Chinese run note**

Record whether qwen2.5 remains robust under stress and what that means for the research direction.

