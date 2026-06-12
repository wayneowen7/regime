# Pilot 实现状态记录

日期：2026-06-01

## 当前状态

Regime-aware Moderation Memory pilot v2 已完成第一版可运行 scaffold。

这一版不是完整 LLM agent 实验，而是 **retrieval-side pilot**：它验证在同一批 precedent/test cases 上，naive semantic memory、policy-only、regime-filtered 和 regime-aware memory 会激活哪些历史 precedent，以及这些 precedent 在 active regime 下是否有效。

2026-06-02 更新：

- 已新增最小 LLM agent loop。
- 已支持 Ollama HTTP API。
- 已在 4090 服务器上运行 `llama3.2:latest` 和 `qwen2.5:7b` smoke/full pilot。
- 详细远端记录见 `docs/research_notes/2026-06-02-remote-gpu-run.md`。

## 已创建文件

数据文件：

- `pilot/data/policies.json`
- `pilot/data/precedents.jsonl`
- `pilot/data/test_cases.jsonl`

代码文件：

- `pilot/src/regime_pilot/__init__.py`
- `pilot/src/regime_pilot/schema.py`
- `pilot/src/regime_pilot/retrieval.py`
- `pilot/src/regime_pilot/conditions.py`
- `pilot/src/regime_pilot/evaluate.py`
- `pilot/src/regime_pilot/run_pilot.py`
- `pilot/src/regime_pilot/llm_pilot.py`
- `pilot/src/regime_pilot/ollama_client.py`
- `pilot/src/regime_pilot/run_llm_pilot.py`

测试文件：

- `tests/test_schema.py`
- `tests/test_retrieval.py`
- `tests/test_conditions.py`
- `tests/test_evaluate.py`
- `tests/test_run_pilot.py`
- `tests/test_llm_pilot.py`
- `tests/test_run_llm_pilot.py`

结果文件：

- `pilot/results/retrieval_metrics.json`
- `pilot/results/llm_qwen25_7b_10cases_4conds_final.json`
- `pilot/results/llm_llama32_10cases_4conds.json`

## 已执行验证

使用 Codex 桌面内置 Python：

`C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`

执行过的命令：

```powershell
$env:PYTHONPATH='pilot/src'; & 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
```

结果：

```text
Ran 22 tests in 0.010s
OK
```

运行 pilot：

```powershell
$env:PYTHONPATH='pilot/src'; & 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m regime_pilot.run_pilot --output pilot/results/retrieval_metrics.json
```

结果：

```text
wrote pilot\results\retrieval_metrics.json
```

## 当前 retrieval-side 结果

`pilot/results/retrieval_metrics.json` 的 summary：

```json
{
  "naive_memory": {
    "n": 10,
    "mean_invalid_activation_rate": 0.3,
    "mean_retrieved_count": 3.0
  },
  "policy_only": {
    "n": 10,
    "mean_invalid_activation_rate": 0.0,
    "mean_retrieved_count": 0.0
  },
  "regime_aware": {
    "n": 10,
    "mean_invalid_activation_rate": 0.0,
    "mean_retrieved_count": 3.0
  },
  "regime_filtered": {
    "n": 10,
    "mean_invalid_activation_rate": 0.0,
    "mean_retrieved_count": 3.0
  }
}
```

解释：

- `naive_memory` 会激活一部分 active regime 下无效的 precedent，当前均值为 `0.3`。
- `regime_aware` 在当前 seed 数据上把 invalid activation 降到 `0.0`。
- `regime_filtered` 也为 `0.0`，这是预期中的强 baseline；后续必须设计更难的 partial/compatible/invariant cases，证明 regime-aware 不只是 metadata filtering。
- `policy_only` 没有 retrieval，所以 invalid activation 是 `0.0`，但它无法证明 memory utility。

## 与完整论文实验的差距

当前 scaffold 只覆盖：

- schema 校验；
- transparent lexical retrieval；
- 四种 memory selection condition；
- retrieval-side invalid activation；
- seed 数据和可复现 runner。
- 最小 LLM agent prompt；
- Ollama client；
- exact decision adherence；
- coarse decision family adherence；
- invalid/unknown used precedent 记录。

尚未覆盖：

- 大规模 LLM agent 结果；
- 更可靠的 within-regime consistency gain；
- stale rationale rate；
- cross-regime contamination rate；
- LM judge 或人工标注校准。

## 下一步

下一步应该接入一个最小 LLM agent/judge loop：

1. 用当前 retrieval condition 构造 prompt。
2. 让 agent 输出结构化 JSON：`decision`、`rationale`、`used_precedents`。
3. 用 judge 或人工小样本判断 policy adherence、stale rationale 和 contamination。
4. 增加 within-regime utility 设计，让 `Policy Only` 与 memory 条件在边界案例上拉开差距。
5. 重点比较 `regime_filtered` 与 `regime_aware`：如果二者继续完全相同，需要加入 compatible/invariant memory、缺失 regime label 或 policy-diff reasoning。

## 环境说明

当前环境中：

- `pytest` 不在 PATH，也没有安装在内置 Python 中。
- 因此实现计划和测试改用 stdlib `unittest`。
- `git` 不在 PATH，因此本轮无法 commit。
