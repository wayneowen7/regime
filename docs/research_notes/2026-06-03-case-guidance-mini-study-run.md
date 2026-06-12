# Case-Guidance Gap Mini-Study 运行记录

日期：2026-06-03

## 目标

这次 mini-study 的目标不是做论文主实验，而是确认 **case-guidance gap** 是否比 T-003 孤例更稳：

> policy-only guidance 是否在边界 case 上不够具体？historical memory 是否可能引入 stale precedent risk？current-policy-valid case guidance 是否能补足具体性而减少旧例风险？

## 数据设计

新增数据：

- `pilot/data/mini_case_guidance_cases.jsonl`
- `pilot/data/mini_case_guidance_precedents.jsonl`
- `pilot/data/mini_case_guidance_stale_precedents.jsonl`
- `pilot/data/mini_case_guidance_current_precedents.jsonl`

设计原则：

- 10 个 matched boundary cases。
- 覆盖 5 类 policy rule：`voting_procedure`、`candidate_claims`、`ballot_validity`、`counting_process`、`satire`。
- 每个 case 都有一个语义相似但 policy-invalid 的旧 regime precedent，以及一个当前 regime 下有效的 guidance precedent。
- 主实验设置沿用 qwen stress setting：`memory_view=operational`、`policy_view=brief`、`stale_warning=off`。

本地 sanity check：

- schema 校验通过。
- 在 mixed precedent pool 中，10/10 个 case 的 `naive_memory` top-3 都包含 invalid old precedent。
- `regime_aware` top-3 不包含 invalid precedent。

注意：`stale_precedents` 和 `current_precedents` 是诊断性 global pool。由于一个 precedent 对某个 case 是 stale，但对另一个同 regime case 可能是 compatible，因此这些 ablation 不是完美因果隔离，只用于观察 memory pool 组成变化对模型行为的影响。

## 远端验证

远端环境：

`lenovo@10.147.18.151:/home/lenovo/code/regime_moderation_pilot`

远端测试：

```text
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m unittest discover -s tests -v
Ran 27 tests in 0.006s
OK
```

## 运行结果

### qwen2.5:7b mixed pool

结果文件：

`pilot/results/llm_qwen25_7b_case_guidance_mini_brief_off.json`

| condition | exact | family | explicit invalid use | heuristic overlap |
|---|---:|---:|---:|---:|
| policy_only | 0.70 | 0.90 | 0.00 | 0.00 |
| naive_memory | 0.90 | 1.00 | 0.00 | 1.00 |
| regime_aware | 0.90 | 1.00 | 0.00 | 0.00 |

解释：

- qwen2.5:7b 在 mixed pool 中没有显式使用 invalid precedent。
- `naive_memory` 和 `regime_aware` 都比 `policy_only` 更好。
- 这说明当 valid current guidance 和 stale guidance 同时出现时，强模型能够挑对依据；mixed pool 没有复现 T-003 那种显式污染。
- `heuristic overlap=1.00` 只表示 naive context 中存在与输出 rationale 词面重叠的 invalid precedent，需要人工复核；它不能直接当作污染率。

### qwen2.5:7b stale-heavy pool

结果文件：

`pilot/results/llm_qwen25_7b_case_guidance_mini_stale_pool_brief_off.json`

| condition | exact | family | explicit invalid use | heuristic overlap |
|---|---:|---:|---:|---:|
| policy_only | 0.70 | 0.90 | 0.00 | 0.00 |
| naive_memory | 0.80 | 0.90 | 0.20 | 0.90 |
| regime_aware | 0.70 | 1.00 | 0.00 | 0.00 |

关键现象：

- `naive_memory` 出现 explicit invalid precedent use，均值 0.20。
- `MCG-T-002` 中，policy-only 已经把明显 satirical candidate claim 误判为 `remove`；stale-heavy naive memory 显式使用无效 election precedent `MCG-E-002`，继续输出 `remove`，并给出更像当前资格误导的 rationale。
- `regime_aware` 在同一 case 中输出 `allow`，回到正确 family。

这说明 stale-heavy historical guidance 可以强化或固化 policy-only 的边界错误。它不是一个干净的 “policy-only 正确、naive 错误” 因果例子，但它支持 case-guidance gap 的第二部分：旧 precedent 在边界 case 中会把模型推向过时或过严的操作化。

### qwen2.5:7b current-heavy pool

结果文件：

`pilot/results/llm_qwen25_7b_case_guidance_mini_current_pool_brief_off.json`

| condition | exact | family | explicit invalid use | heuristic overlap |
|---|---:|---:|---:|---:|
| policy_only | 0.70 | 0.90 | 0.00 | 0.00 |
| naive_memory | 0.90 | 1.00 | 0.00 | 0.60 |
| regime_aware | 0.90 | 1.00 | 0.00 | 0.00 |

关键现象：

- current-heavy guidance 将 `MCG-T-002` 从 policy-only 的 `remove` 修正为 `contextualize`。
- qwen 使用当前有效 precedent `MCG-N-002`，rationale 直接指出 obvious satire and no actionable voting misinformation。
- 这支持 case-guidance gap 的第一部分：policy-only 对边界 case 可能过度执行，当前有效 case guidance 能补足操作边界。

### llama3.2 mixed pool 对照

结果文件：

`pilot/results/llm_llama32_case_guidance_mini_brief_off.json`

| condition | exact | family | explicit invalid use | heuristic overlap |
|---|---:|---:|---:|---:|
| policy_only | 0.30 | 0.80 | 0.00 | 0.00 |
| naive_memory | 0.80 | 0.90 | 0.00 | 1.00 |
| regime_aware | 0.80 | 0.90 | 0.00 | 0.00 |

解释：

- llama3.2 的 policy-only 明显更弱。
- memory guidance 明显提升 exact adherence。
- 但 mixed pool 中 naive 与 regime-aware 的 family-level 表现相同，且没有 explicit invalid precedent use。
- `MCG-T-010` 中 naive 和 regime-aware 都输出 `remove`，说明该 case 的 normal-regime expected `allow` 可能过于宽松，或者当前 guidance 不足以让模型识别 pretend-election satire。

## 对问题定义的影响

这次 mini-study 让问题更清楚，但也限制了 claim：

### 支持的结论

1. **Policy-only 确实存在边界不足**
   - qwen2.5:7b 在 `MCG-T-002` 上把 obvious satire 判成 `remove`。
   - llama3.2 policy-only exact 更低，说明 case-level guidance 对较弱模型更重要。

2. **Current-policy-valid guidance 有实用价值**
   - qwen2.5:7b current-heavy pool 和 regime-aware guidance 都能修正 `MCG-T-002`。
   - mixed pool 中，只要 valid guidance 可见，qwen 通常能选择正确依据。

3. **Stale-heavy historical guidance 有风险**
   - qwen2.5:7b stale-heavy pool 出现 explicit invalid precedent use。
   - `MCG-T-002` 显示 stale election precedent 会强化过严判断。

### 不支持的结论

1. **不支持“mixed historical memory 一定有害”**
   - qwen2.5:7b 在 mixed pool 中没有显式使用 invalid precedent。
   - naive 和 regime-aware 都提升了表现。

2. **不支持“只要有 invalid precedent 出现在 context 就会污染”**
   - invalid precedent 被检索到不等于被模型显式使用。
   - 强模型会在 valid guidance 同时存在时抵抗旧例。

3. **不支持把 heuristic overlap 当污染率**
   - heuristic overlap 在 mixed/current pool 中很高，但没有伴随 explicit invalid use 或 family harm。
   - 后续必须用人工 label 或更严格 rubric。

## 当前最稳的问题表述

mini-study 后，建议把论文问题写得更精确：

> Dynamic moderation agents face a case-guidance gap: policy-only instructions can be too abstract for boundary cases, while stale-heavy historical guidance can reinforce outdated operationalizations. The key question is how to provide current-policy-valid case guidance without treating historical precedents as timeless evidence.

这比“历史记忆会污染”更稳，因为它同时容纳了两个结果：

- current guidance 有 utility；
- stale-heavy guidance 有 risk；
- mixed historical memory 对强模型未必立刻有害。

## 下一步

不要马上扩 60-100 case。下一步应做一个更干净的 matched ablation：

1. 分开 active election cases 和 active normal cases，避免 global pool 中一个 case 的 stale precedent 对另一个 case 变成 compatible。
2. 为每个 case 控制三种输入：
   - policy-only；
   - stale-only guidance；
   - current-valid guidance。
3. 手工标注 rationale contamination，而不是依赖 token overlap。
4. 重点寻找两类 case：
   - policy-only 错，current-valid guidance 修正；
   - policy-only 对，stale-only guidance 带偏。

如果第二类很少，论文可以转向 “case guidance improves dynamic moderation, stale-heavy historical examples are a risk under certain conditions”，而不是把 contamination 作为主轴。

