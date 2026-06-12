# POLAR-Compact 技术方案与下一步实验计划

## 当前定位

我们当前选择的主线是：

> **POLAR-Compact: Boundary-Action Data Guided Policy Operationalization Compiler**

它不是单纯的 prompt rewriting，也不是 BARRED-like 的合成训练数据路线。它的目标是把高层 moderation policy 转成可执行、短小、跨模型可迁移的 operational prompt，同时用 boundary-action contrast data 验证这个 prompt 修复的是哪类 policy-to-operation gap。

## 三层产物

| 层次 | 产物 | 用途 |
|---|---|---|
| 部署层 | `P+`: compact operational prompt | 给闭源或开源 LLM 直接执行审核 |
| 数据层 | `D_ba`: boundary-action probes / contrast sets | 暴露、定位、验证 boundary/action gap |
| 方法层 | IR / compiler / gap localizer | 把高层 policy 编译成 `P+`，并输出 sidecar 供研究分析 |

最终部署 prompt 不携带证据链。证据、来源、contrast set、gap report 只作为 sidecar，用于调试、论文分析和复现实验。

## 和 BARRED 的区别

BARRED 的核心路线可以概括为：

```text
custom policy/task description + examples -> synthetic labeled moderation data -> train guardrail classifier
```

我们的路线是：

```text
high-level policy -> boundary/action IR -> contrast probes -> compact operational prompt
```

因此，我们的数据不是普通 `content -> label` 样本，而是 `boundary variable -> action edge` 的 matched contrast data。它的目的不是堆训练集，而是定位哪一个变量应该改变 moderation action。

## 和 prompt optimization 的区别

Prompt optimization 通常优化：

```text
wording -> score
```

POLAR-Compact 优化：

```text
policy semantics -> boundary/action IR -> compact operational prompt -> behavior validation
```

必须做 length-controlled baseline，避免被解释成“只是 prompt 更长”。也必须做 LLM rewrite baseline，避免被解释成“让模型把 policy 写详细”。

## 已实现的 v0 代码

新增模块：

- `pilot/src/regime_pilot/polar_compact.py`

核心能力：

1. `build_policy_ir`
   - 从半结构化 policy JSON 中抽取 policy id、description、boundary rule、action rubric。
2. `compile_compact_policy`
   - 把单个 policy rule 编译成短小 operational prompt。
   - prompt 包含 action space、boundary、action rubric、uncertainty/escalation rule、JSON 输出约束。
   - prompt 不包含 `supporting_probes` 或 `evidence_trace`。
3. `build_boundary_action_contrast_sets`
   - 从现有 action-granularity cases 的 `expected_rationale` 中抽取 `boundary_family`、`action_contrast`、`boundary_variables`。
   - 生成 family/edge 级别 contrast set。
4. CLI:

```powershell
$env:PYTHONPATH='pilot/src'
python -m regime_pilot.polar_compact `
  --policies pilot/data/action_granularity_policies_action_rubric.json `
  --output-policies pilot/data/polar_compact_policies_action_granularity.json `
  --output-sidecar pilot/data/polar_compact_sidecar_action_granularity.json `
  --cases pilot/data/action_granularity_cases.jsonl `
  --output-contrast-sets pilot/data/polar_compact_contrast_sets_action_granularity.json
```

## 已生成的 v0 数据产物

- `pilot/data/polar_compact_policies_action_granularity.json`
- `pilot/data/polar_compact_sidecar_action_granularity.json`
- `pilot/data/polar_compact_contrast_sets_action_granularity.json`

这些产物用于第一轮对照实验。当前版本仍然是 deterministic compiler，不声称已经训练出 policy compiler model。

## 第一轮实验矩阵

先在 election moderation / 12 action-granularity probes 上跑：

| 条件 | policy 文件 | 作用 |
|---|---|---|
| abstract | `action_granularity_policies_abstract.json` | 高层 policy baseline |
| action_rubric | `action_granularity_policies_action_rubric.json` | 人写 action rubric 上界之一 |
| polar_compact | `polar_compact_policies_action_granularity.json` | 当前 deterministic compiler 输出 |

模型：

- `qwen2.5:7b`
- `llama3.2:latest`

后续稳定后再扩展：

- `qwen2.5:14b`
- `qwen3:14b`
- 闭源模型 API，如果成本允许

指标：

- exact-action error
- decision-family error
- action-granularity error
- boundary instability
- prompt length
- new harm / over-escalation case

## 远端运行脚本

新增脚本：

- `scripts/run_2026_06_12_polar_compact_experiments.ps1`

它会：

1. 同步 `docs/pilot/tests/scripts` 到 4090 远端；
2. 跑 unittest；
3. 在远端生成 POLAR-Compact policy / sidecar / contrast sets；
4. 串行跑 `abstract/action_rubric/polar_compact` 对照；
5. 生成 analyzer 和 compare 输出；
6. 把结果拉回本地 `pilot/results/`。

## 当前验收标准

第一阶段不要求 POLAR-Compact 超过人工 action rubric，因为当前 deterministic compiler 的输入本来来自 action rubric。第一阶段要确认的是：

1. POLAR-Compact 能接入现有 runner，不破坏现有测试；
2. compact rendering 不降低 action-rubric 的效果；
3. prompt 更短或更清晰时，仍能保持 decision-family / exact-action 信号；
4. contrast set sidecar 能清楚呈现 family/action edge；
5. 后续可以把 action rubric 来源替换成自动 decompiler / active clarification。

## 第二阶段建议

若第一阶段稳定，下一步做真正区分创新性的实验：

1. 增加 `LLM rewrite` baseline：
   - 直接让 LLM 把 abstract policy 改写得更详细。
2. 增加 `length-matched rewrite` baseline：
   - 控制 prompt token/char 数，排除“只是更长”的解释。
3. 增加 `BARRED-like isolated data` baseline：
   - 同样样本预算下，比较 isolated labeled cases 与 matched boundary-action contrast sets。
4. 训练小型 policy compiler 可作为第三阶段：
   - 输入：high-level policy + action space + few contrast sets。
   - 输出：boundary/action IR + compact operational prompt。

## 当前不能过度 claim

- 不能声称已经自动恢复真实 policy boundary。
- 不能声称 proof/evidence 应该进入最终 prompt。
- 不能声称 v0 已经优于所有 prompt optimization 方法。
- 不能把 action rubric 与 boundary clarification 混为一谈。

当前最稳的 claim 是：

> Boundary-action contrast data can support a policy operationalization compiler that renders high-level moderation policies into compact executable prompts, while preserving analyzable distinctions between boundary-family errors and exact-action errors.
