# POLAR-Active 方法设计

## 目标

POLAR-Active 的目标是把当前的 policy-to-operation gap 方向从“人工写更细 policy prompt”推进为一个可复现的方法：

> 给定高层自然语言 moderation policy、目标动作空间和少量诊断 probes，自动定位缺失的 boundary/action 约束，并把它们编译成可部署的 operational policy。

它不是普通 prompt rewrite，也不是 BARRED-like synthetic training data。它的核心对象是 **policy specification repair**：先诊断 policy specification 缺什么，再生成结构化 patch，最后编译成紧凑的执行 policy。

## 当前证据基础

已有实验支持两层 gap：

- `boundary clarification` 主要降低 decision-family error。
- `action rubric` 进一步降低 exact-action error。

DynaBench 100-case v0 中：

- qwen2.5:7b：`boundary` 让 family adherence 从 `0.5600` 到 `0.7800`，`action_rubric_v2` 让 exact adherence 从 `0.4200` 到 `0.7900`。
- llama3.2：`boundary` 让 family adherence 从 `0.6400` 到 `0.7700`，`action_rubric_v2` 让 exact adherence 相比 boundary 从 `0.4400` 到 `0.6800`。

POLAR-Compact / rewrite baseline 进一步说明：

- 普通 template rewrite 和 length-matched rewrite 不能充分解决 action-granularity error。
- 结构化 boundary-action cues 有价值，但 deterministic compiler 仍有 cue selection、cue weighting、conflict handling 的缺口。

## 研究问题

POLAR-Active 要回答三个问题：

1. 高层 policy 的失效是否可以被定位为缺失的 boundary/action specification，而不是泛泛的“模型能力不足”？
2. 自动发现并修复这些 specification gaps，是否比普通 prompt rewrite 更稳定地提升 exact-action adherence？
3. 自动生成的 operational policy 是否能跨模型迁移，同时控制 prompt 长度和 over-removal harm？

## 方法总览

POLAR-Active 包含 6 个阶段：

```text
high-level policy + action space
-> policy decompiler
-> diagnostic probe generator
-> target model evaluator
-> gap localizer
-> IR patch proposer + verifier
-> operational policy compiler
```

最终部署给审核模型的是 compiled operational policy。诊断 probes、patch 来源和验证结果保留在 sidecar，用于论文分析、调试和审计，不进入最终 prompt。

## 阶段 1：Policy Decompiler

输入：

- high-level policy text
- action space，例如 `allow/remove` 或 `allow/contextualize/restrict/remove/escalate`
- optional source policy metadata，例如 domain、risk level、platform constraints

输出：`PolicyIR`

```json
{
  "policy_id": "string",
  "action_space": ["allow", "remove"],
  "rules": [
    {
      "rule_id": "string",
      "intent": "high-level policy intent",
      "boundary_variables": [],
      "action_edges": [],
      "priority_rules": [],
      "uncertainty_rule": "string"
    }
  ]
}
```

`boundary_variables` 表示可能改变 decision family 的变量。`action_edges` 表示同一 family 内部导致 exact action 改变的变量。例如：

```json
{
  "from": "contextualize",
  "to": "remove",
  "condition": "official-looking current election notice with weak parody marker",
  "required_cues": ["official_format", "current_disruption", "weak_parody_label"],
  "forbidden_shortcut": "Do not treat any parody label as sufficient by itself."
}
```

第一版 decompiler 可以由 LLM 生成候选 IR，再由 schema validator 和 rule normalizer 清洗。后续可以把 accepted IR patches 蒸馏成小模型。

## 阶段 2：Diagnostic Probe Generator

probe generator 不生成训练数据，而生成 matched diagnostic probes。每组 probes 只改变一个或少数 boundary/action 变量，用来测试 policy 是否足以规定边界和动作。

输入：

- `PolicyIR`
- known failure families，例如 satire/deceptive notice、education/endorsement、prediction/certification
- probe budget，例如每条 rule 4-8 条

输出：`DiagnosticProbeSet`

```json
{
  "probe_id": "string",
  "rule_id": "string",
  "boundary_family": "string",
  "changed_variables": ["string"],
  "expected_decision_family": "non_removal|intervention",
  "expected_action": "allow|contextualize|restrict|remove|escalate",
  "rationale_anchor": "why this variable should change the action"
}
```

probe 需要满足三个约束：

- matched：同组 probes 尽量只改目标变量。
- minimal：避免堆砌无关文本。
- action-discriminative：至少覆盖一个会改变 exact action 的 edge。

## 阶段 3：Target Model Evaluator

对同一批 probes 跑多个 policy condition：

- original policy
- generic rewrite baseline
- length-matched rewrite baseline
- current compiled policy
- patched compiled policy
- optional human action rubric upper bound

输出保留 raw model result，但 committed summary 只保留无原文统计。

核心指标：

- exact-action adherence
- decision-family adherence
- action-binding error
- boundary error
- instability across models / seeds
- over-removal harm：`allow -> remove/escalate`
- under-enforcement harm：`remove/escalate -> allow`
- prompt length
- patch efficiency：每个 accepted patch 带来的错误下降

## 阶段 4：Gap Localizer

gap localizer 将错误解释为 specification gaps。

输入：

- probe metadata
- model outputs
- current `PolicyIR`

输出：`GapReport`

```json
{
  "gap_id": "string",
  "rule_id": "string",
  "gap_type": "missing_boundary|missing_action_edge|wrong_priority|overbroad_default|ambiguous_uncertainty",
  "error_pairs": ["allow->remove"],
  "affected_probe_ids": [],
  "candidate_cues": [],
  "harm_direction": "over_removal|under_enforcement|wrong_action_granularity",
  "confidence": 0.0
}
```

gap 类型定义：

- `missing_boundary`：decision family 错误，例如应干预却判成 non-removal。
- `missing_action_edge`：family 正确但 exact action 错误，例如应 contextualize 却 remove。
- `wrong_priority`：两个 cue 同时出现时优先级错，例如 parody label 覆盖了 current official notice。
- `overbroad_default`：模型学到“敏感就删”或“复杂就升级”。
- `ambiguous_uncertainty`：policy 没说不确定时该 allow、remove 还是 escalate。

## 阶段 5：IR Patch Proposer 与 Verifier

patch proposer 根据 `GapReport` 生成结构化 patch，而不是直接改写 prompt。

Patch 类型：

- `add_boundary_variable`
- `add_action_edge`
- `add_priority_rule`
- `add_uncertainty_rule`
- `add_forbidden_shortcut`
- `remove_or_weaken_overbroad_rule`

示例：

```json
{
  "patch_type": "add_priority_rule",
  "rule_id": "satire",
  "condition": "official-looking current election disruption notice with weak parody label",
  "priority_rule": "Current election disruption and official-looking format override weak parody markers.",
  "expected_effect": "reduce allow->remove/remove->allow instability around deceptive notices",
  "length_budget_chars": 180
}
```

Verifier 需要检查：

- schema validity：patch 是否符合 IR schema。
- non-contradiction：是否和已有 action edge 冲突。
- local rescue：是否修复目标 gap。
- no-harm：是否伤害 held-out probes。
- length budget：是否超过每条 rule 的长度预算。
- cross-model transfer：在 qwen/llama 至少不出现明显反向伤害。

第一版 verifier 可以是规则检查 + 小矩阵执行。后续可以增加 judge model，但 judge 只做辅助，不作为唯一真值。

## 阶段 6：Operational Policy Compiler

compiler 将 patched IR 编译成 deployment prompt。

要求：

- prompt 中只放必要 boundary/action 约束。
- sidecar 中保留 gap report、patch provenance、probe ids、验证统计。
- 不把 raw probes、case text、长证据链放入 deployment prompt。
- 支持 length budget，例如每条 rule 不超过 action rubric baseline 的 1.0x 或 1.2x。

输出：

- `compiled_policy.json`
- `compiler_sidecar.json`
- `gap_report.json`
- `text_free_eval_summary.json`

## 与已有方法的边界

### 不是普通 prompt rewrite

普通 rewrite 优化的是 wording。POLAR-Active 优化的是结构化 specification：

```text
policy semantics -> boundary/action IR -> verified patches -> compiled policy
```

因此必须做 template rewrite、length-matched rewrite、strong LLM rewrite 三类 baseline。

### 不是 BARRED-like synthetic training data

BARRED-like 路线的核心是构造 labeled examples 训练 guardrail。POLAR-Active 生成 probes 的目的不是扩充训练集，而是定位 policy specification 缺失项。

因此 evaluation 要报告 patch efficiency、gap localization accuracy、held-out no-harm，而不只报告最终分类分数。

### 不是 DynaGuard runtime judging

DynaGuard-like 路线是给定 policy 后训练/调用 guardian model 直接判断。POLAR-Active 的目标是生成可迁移的 operational policy，让不同目标模型都能更稳定执行同一 policy。

因此必须测 cross-model transfer。

## 第一版实现范围

第一版只做 agentic compiler，不做 LoRA/RL。

范围内：

- 复用现有 `run_llm_pilot.py`、DynaBench artifacts、POLAR-Compact schema。
- 新增 `polar_active.py`，实现 IR patch、gap localizer、compiler。
- DynaBench 先做 `allow/remove` 两动作版。
- action-granularity probes 做多动作版。
- 输出 text-free summaries。

范围外：

- 不训练审核模型。
- 不复现 BARRED 全流程。
- 不把 generated probes 当训练集。
- 不声称自动恢复真实平台 policy，只声称诊断和修复 operational underspecification。

## 实验矩阵

### DynaBench allow/remove

目的：验证 boundary/action binding 对二元动作空间也有用。

条件：

- original/abstract policy
- boundary policy
- action_rubric_v2
- template rewrite
- length-matched rewrite
- POLAR-Active compiled policy

模型：

- qwen2.5:7b
- llama3.2:latest
- optional qwen3:14b

验收：

- exact adherence 高于 original/boundary。
- 相比 action_rubric_v2 至少接近，或在 prompt length/no-harm 上更好。
- over-removal harm 不高于 action_rubric_v2。

### Action-granularity multi-action probes

目的：验证 POLAR-Active 能处理 `contextualize/remove/escalate` 等动作粒度。

条件：

- abstract
- template rewrite
- length-matched rewrite
- human action rubric
- POLAR-Compact
- POLAR-Active

重点 family：

- satire/deceptive official-looking notice
- education/critique quote vs endorsement
- mobilization escalation

验收：

- 保持 AG-T-002、AG-T-004 成功。
- 修复 AG-T-005/006/007/008 至少两个不稳定 case。
- family error 接近 human action rubric。
- exact-action error 不高于 POLAR-Compact。
- 平均 prompt 长度不超过 human action rubric 的 1.2x。

## 可能的 LoRA/RL 扩展

若 agentic compiler v1 有稳定信号，再做 compiler distillation。

训练数据来自：

```text
(policy, gap report, accepted IR patch, compiled policy, eval delta)
```

LoRA 模型任务：

- `policy -> initial IR`
- `gap report -> IR patch`
- `IR -> compact operational policy`

RL reward：

- held-out exact-action improvement
- no-harm penalty
- prompt length penalty
- cross-model transfer reward
- schema validity reward

这条扩展的定位是训练 policy compiler，而不是训练 moderation classifier。

## 风险与应对

风险 1：被认为只是 prompt optimization。

应对：必须保留 IR、patch、gap localization、matched probes，并与普通 rewrite / length-matched rewrite 对比。

风险 2：自动生成 probes 的真值不可靠。

应对：v1 中 probes 只用于诊断候选 gap；最终 claim 依赖 held-out labeled benchmark 和人工审核小样本。

风险 3：patch 过拟合当前 probes。

应对：probe split、held-out family、cross-model transfer、no-harm check。

风险 4：prompt 越修越长。

应对：每条 rule 设置 length budget，报告 patch efficiency，sidecar 留证据但 deployment prompt 只保留必要规则。

风险 5：方法过重。

应对：v1 只实现最小闭环：localize one gap family -> propose patch -> verify -> compile -> evaluate。

## 最小可行闭环

第一轮只做一个小闭环：

1. 输入 DynaBench 100-case artifacts 和 action-granularity probes。
2. 从现有错误中自动生成 `GapReport`。
3. 针对 satire/deceptive notice 或 DynaBench allow/remove 错误生成 2-4 个 IR patches。
4. 编译 patched policy。
5. 远端跑 qwen2.5:7b 和 llama3.2。
6. 输出 text-free summary。
7. 判断是否同时满足：
   - exact-action adherence 提升；
   - boundary/action 错误下降；
   - prompt length 受控；
   - no-harm 不恶化；
   - 至少一个 patch 跨模型有效。

## 论文表述

主 claim：

> We formulate moderation policy deployment as a specification repair problem. Instead of rewriting prompts or synthesizing training labels, POLAR-Active diagnoses missing boundary-action constraints through matched probes, proposes verified IR patches, and compiles them into operational policies that improve exact moderation actions while preserving auditability.

中文表述：

> 我们将内容审核 policy 的落地问题建模为 specification repair：高层 policy 不仅需要说明边界，还需要说明边界如何映射到具体操作动作。POLAR-Active 通过 matched diagnostic probes 定位缺失的 boundary/action 约束，生成可验证的 IR patch，并将其编译成可部署的 operational policy。

## 不应过度声明

- 不声明 POLAR-Active 能自动发现真实平台完整 policy。
- 不声明 probes 的 synthetic labels 可以替代人工 policy owner。
- 不声明 prompt compiler 永远优于训练 guardrail。
- 不声明当前 v1 是最终自动化系统。
- 不把 sidecar evidence 放进 deployment prompt 后再宣称效率高。
