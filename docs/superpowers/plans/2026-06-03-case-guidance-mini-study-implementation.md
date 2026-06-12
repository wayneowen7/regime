# Case Guidance Mini Study Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建并运行一个 10-case matched boundary mini-study，用于确认 dynamic moderation 中的 case-guidance gap 是否不是 T-003 孤例。

**Architecture:** 不改现有 runner。新增一组 mini-study precedents 和 test cases，复用 `regime_pilot.run_llm_pilot` 的 `policy_only`、`naive_memory`、`regime_aware` 三个条件。主 stress 设置使用 `memory_view=operational`、`policy_view=brief`、`stale_warning=off`。

**Tech Stack:** Python stdlib, JSONL, existing `regime_pilot` runner, Ollama on remote 4090.

---

## 文件结构

- Create: `pilot/data/mini_case_guidance_precedents.jsonl`
  - 20 条 precedent，每个 matched case 对应一个旧 regime invalid precedent 和一个当前 regime valid precedent。
- Create: `pilot/data/mini_case_guidance_cases.jsonl`
  - 10 条 boundary test cases，覆盖 voting procedure、candidate claims、ballot validity、counting process、satire。
- Create: `docs/research_notes/2026-06-03-case-guidance-mini-study-run.md`
  - 中文记录设计、命令、结果、关键案例和 claim 边界。
- Modify: `docs/research_notes/2026-06-01-artifact-index.md`
  - 加入 mini-study 数据、结果和记录。

## Task 1: Matched data

- [ ] **Step 1: Create mini-study JSONL data**

Write 10 matched boundary cases. Each case must have:

- one semantically similar invalid historical precedent from the opposite regime;
- one current-regime valid guidance precedent;
- expected decision and expected rationale;
- `invalid_precedent_regimes` matching the invalid side.

- [ ] **Step 2: Validate schema locally**

Run:

```powershell
$env:PYTHONPATH='pilot/src'; python - <<'PY'
from pathlib import Path
from regime_pilot.schema import load_jsonl, validate_precedent, validate_test_case
for record in load_jsonl(Path("pilot/data/mini_case_guidance_precedents.jsonl")):
    validate_precedent(record)
for record in load_jsonl(Path("pilot/data/mini_case_guidance_cases.jsonl")):
    validate_test_case(record)
print("ok")
PY
```

Expected: `ok`.

## Task 2: Retrieval sanity

- [ ] **Step 1: Check that naive retrieves invalid candidates**

Run a small local script that prints top-3 naive and regime-aware retrieved case ids for all 10 cases.

Expected:

- `naive_memory` often includes the invalid historical precedent.
- `regime_aware` removes invalid historical precedents and keeps current-regime valid guidance.

## Task 3: Remote experiments

- [ ] **Step 1: Sync to 4090**

Upload `docs/`, `pilot/`, and `tests/` to `/home/lenovo/code/regime_moderation_pilot`.

- [ ] **Step 2: Remote test**

Run:

```bash
cd /home/lenovo/code/regime_moderation_pilot
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 3: Run qwen2.5**

Run:

```bash
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m regime_pilot.run_llm_pilot \
  --model qwen2.5:7b \
  --conditions policy_only,naive_memory,regime_aware \
  --top-k 3 \
  --limit-cases 10 \
  --memory-view operational \
  --policy-view brief \
  --stale-warning off \
  --precedents pilot/data/mini_case_guidance_precedents.jsonl \
  --test-cases pilot/data/mini_case_guidance_cases.jsonl \
  --output pilot/results/llm_qwen25_7b_case_guidance_mini_brief_off.json
```

- [ ] **Step 4: Run llama3.2 as sensitivity check**

Run the same command with `--model llama3.2:latest` and output:

`pilot/results/llm_llama32_case_guidance_mini_brief_off.json`

## Task 4: Analysis note

- [ ] **Step 1: Pull results**

Pull both JSON files to local `pilot/results/`.

- [ ] **Step 2: Summarize**

Report:

- exact adherence;
- family adherence;
- invalid used precedents;
- heuristic overlap, explicitly labeled as review signal;
- cases where `policy_only` and `regime_aware` are correct but `naive_memory` fails.

- [ ] **Step 3: Write run note**

Write a Chinese run note with conservative claim boundaries.

