# clarified policy 与 BARRED-like 前半段对照：结果分析模板与论文判断说明

日期：2026-06-08

## 目的

这份说明服务两个下一步实验：

1. `clarified policy patch` 对照：比较 `abstract policy` vs `clarified policy`。
2. `BARRED-like synthetic/debate` 前半段对照：从同一 policy 生成 `boundary candidates`，再用 `judge/debate labels` 评估 `sample yield`、`agreement`、`anchor agreement` 与 `pseudo_consensus_candidates`。

这两步不是为了立刻扩成大 benchmark，而是为了回应两个最直接的质疑：

- 质疑 A：如果 `policy` 写清楚就可以了，为什么需要 Boundary Sufficiency？
- 质疑 B：BARRED 已经用 synthetic data 和 debate 处理了边界样本，为什么还要单独做 policy boundary diagnosis？

核心回答应保持克制：

> 我们不是否认 clarified policy 或 synthetic data 的价值；我们要测试的是，在生成、筛选或训练 boundary examples 之前，policy text 是否已经足以指定要合成和执行的边界。

## 实验一：`clarified policy patch` 对照

### 要检验的问题

对每个高错误或高不稳定的 `boundary family`，写一个最小 `clarified policy patch`，只补足当前实验已经识别出的边界变量，不重写整个任务。然后在同一批 matched probes 上比较：

- `abstract policy`
- `abstract policy + clarified policy patch`

推荐至少报告两个 presentation 设置：

- `brief/off`
- `full/on`

如果预算有限，优先跑现有错误最高、最能代表 policy underspecification 的 family。

### 为什么这一步直接回应“policy 写清楚即可”

如果 clarified policy 明显降低 `policy_only_boundary_error_rate` 和 `boundary_instability_rate`，这说明质疑是对的：写清楚确实有用。

但这不会削弱 Boundary Sufficiency，反而给出论文主线：

> Boundary Sufficiency 的价值不是替代好 policy，而是诊断 abstract policy 哪里还没有写清楚，并用小规模 boundary probes 验证 clarification 是否真的修复了执行边界。

如果 clarified policy 没有明显改善，则说明问题不只是 wording 缺失，可能还包括模型 instruction following、概念混淆、prompt 格式、或任务本身存在多目标冲突。

### 实验成功意味着什么

成功标准建议写成方向性门槛，而不是绝对胜负：

- `policy_only_boundary_error_rate` 在 clarified 条件下明显下降。
- `boundary_instability_rate` 在 clarified 条件下明显下降。
- `current_guidance_rescue_rate` 的必要性下降，即 clarified policy 本身承担了部分 rescue 作用。
- rationale 中 `boundary_variable_confusion` 减少。
- family-level 结果能指出哪些边界变量被 patch 修复，哪些没有被修复。

若出现这些信号，可以 claim：

- `clarified policy patch` 能提升 `policy specification sufficiency`。
- Boundary probes 能定位 abstract policy 的 under-specified boundary。
- 当前方法可作为 policy writing / policy repair 的诊断步骤。

不能 claim：

- clarified policy 总能解决所有 boundary failure。
- policy-only 在真实部署中一定足够。
- 这些 probes 已证明某类模型可靠或不可靠。
- 我们恢复了唯一的 `true boundary`。

### 实验失败意味着什么

如果 clarified policy 没有降低 error 或 instability，需要区分三种失败：

1. patch 写得不够清楚：rationale 仍显示模型没有捕捉关键边界变量。
2. policy 已清楚但模型不遵从：更接近 instruction following failure。
3. boundary 本身仍需 policy-owner decision：clarification 未能解决多目标冲突或价值权衡。

失败时可以 claim：

- 单纯把 wording 写长不一定提升 executable boundary stability。
- 需要进一步区分 `policy underspecification` 与 `instruction following failure`。

不能 claim：

- clarified policy 没有价值。
- policy writing 不重要。
- Boundary Sufficiency 已经证明模型无法执行明确规则。

### 必须报告的结果

每个 family 至少报告：

- `n_cases`
- `n_rows`
- `policy_only_boundary_error_rate`
- `boundary_instability_rate`
- `current_guidance_rescue_rate`
- `stale_guidance_harm_rate`，如果 stale 条件也跑了
- `invalid_used_precedent_rate`，如果有 stale 或 memory 条件
- per-family / per-probe error table
- patch 前后 rationale 中的主要 failure mode

建议增加一个 patch-level 表：

| `boundary_family` | `patch_target` | `abstract_error` | `clarified_error` | `abstract_instability` | `clarified_instability` | `interpretation` |
|---|---|---:|---:|---:|---:|---|

`interpretation` 只写诊断，不写胜利宣言。例如：

- `patch_rescues_boundary_variable`
- `patch_partial_rescue`
- `instruction_following_failure_likely`
- `policy_owner_anchor_needed`
- `no_clear_effect`

## 实验二：`BARRED-like synthetic/debate` 前半段对照

### 要检验的问题

从同一份 `abstract policy` 出发，模拟 BARRED-like 流程的前半段：

1. 自动生成 `boundary candidates`。
2. 用 2-3 个 `judge/debate prompts` 给 candidates 打 `judge/debate labels`。
3. 统计生成样本中有多少是可用边界样本，有多少形成高一致性判断，以及这些一致性是否有 current policy anchor 支持。

这一步只测试 synthetic/debate 的前半段可靠性，不训练 guardrail，不比较最终模型性能。

### 为什么这一步直接回应“BARRED 已经做合成数据”

BARRED-like 方法的强项是低成本生成和筛选训练数据。我们的质疑不是“不能生成数据”，而是：

> 如果 source policy 对某些 boundary variable 没有充分指定，那么 synthetic generation 和 debate verification 可能会把未授权的边界补全成看似高一致性的 training signal。

因此要直接测：

- 生成流程能否覆盖真正的 boundary region。
- debate/judge 是否只是提高内部一致性。
- 高一致性 labels 是否与 `expected_current_boundary` 或 current-policy-valid anchors 对齐。

### 实验成功意味着什么

这里的“成功”分两类。

如果实验发现 BARRED-like 流程表现可靠：

- `sample yield` 高。
- `agreement` 高。
- `anchor agreement` 高。
- `pseudo_consensus_candidates` 少或没有。
- 错误主要集中在低质量 candidates，而不是高一致性误判。

则可以 claim：

- 在这些 policy/family 上，BARRED-like 前半段没有明显 pseudo-consensus 风险。
- Boundary Sufficiency 可以作为 synthetic data pipeline 的 preflight audit，而不是替代 BARRED-like 方法。
- 论文主线应更强调 diagnostic compatibility：先测 policy sufficiency，再决定是否安全进入 synthetic training。

如果实验发现 pseudo-consensus 风险：

- `agreement` 高但 `anchor agreement` 低。
- 多个 judge/debate prompts 对同一错误边界高度一致。
- rationale 依赖 policy 中未明说的边界假设。
- `clarified policy patch` 能改变这些 labels。

则可以 claim：

- BARRED-like 前半段可能产生 `pseudo_consensus_candidates`。
- debate/judge agreement 不能单独作为 policy-owner alignment 的证据。
- synthetic boundary generation 需要 policy sufficiency audit 或 current-policy-valid anchor check。

不能 claim：

- BARRED 错。
- debate 没有价值。
- synthetic data 无价值。
- pseudo-consensus candidates 等于真实部署中的训练失败。
- 不训练 guardrail 就能断言最终 BARRED-like 系统性能。

### 实验失败意味着什么

如果 synthetic/debate 流程生成不了足够 candidates：

- 这主要说明当前 generator 或 prompt 不够强，不能直接推断 BARRED-like 方法不可行。
- 报告 `sample yield` 失败，并把后续路线转向 generator/prompt repair 或缩小 family 范围。

如果 candidates 很多但 judge labels 分散：

- 说明 debate/judge 没形成稳定边界。
- 这支持 boundary ambiguity 或 judge instability，但不是 pseudo-consensus。

如果 candidates 和 labels 都稳定且 anchor agreement 高：

- 这削弱“BARRED-like pseudo-consensus risk”作为主线的必要性。
- 论文应避免继续强调 BARRED reliability failure，转向 Boundary Sufficiency 作为 preflight diagnostic。

### 必须报告的结果

生成阶段：

- `n_generated`
- `n_valid_candidates`
- `sample_yield = n_valid_candidates / n_generated`
- `n_boundary_candidates`
- `candidate_family_distribution`
- `duplicate_rate`
- `invalid_candidate_reasons`

judge/debate 阶段：

- `n_labeled`
- `agreement`
- `anchor agreement`
- `policy_clause_support_rate`
- `boundary_variable_confusion_rate`
- `pseudo_consensus_candidates`

建议核心表：

| `boundary_family` | `n_generated` | `sample_yield` | `agreement` | `anchor_agreement` | `pseudo_consensus_candidates` | `interpretation` |
|---|---:|---:|---:|---:|---:|---|

`pseudo_consensus_candidates` 的判定应保守。建议同时满足：

- 多个 judge/debate prompts 给出同一 label 或等价 label。
- 该 label 与 `expected_current_boundary` 或 current-policy-valid anchor 冲突。
- rationale 主要依赖 abstract policy 中未明确指定的边界假设。
- 人工复核认为它不是单纯 parse error、低质量 candidate 或明显 prompt bug。

## 共同分析原则

### 结果解释顺序

每个实验先按以下顺序解释，避免把所有现象都写成同一种失败：

1. candidate 或 probe 是否有效。
2. policy 是否明确指定关键 `boundary_variable`。
3. 模型或 judge 是否遵从明确规则。
4. rationale 是否依赖 stale、invalid 或 unanchored assumptions。
5. agreement 是否有 current-policy-valid anchor 支持。

### 可报告但需谨慎的 claim

可以报告：

- `abstract policy` 下出现可观测的 boundary instability。
- `clarified policy patch` 是否降低 error/instability。
- BARRED-like 前半段是否产生 high-agreement / low-anchor 的 candidates。
- Boundary Sufficiency 作为 synthetic data 前置诊断的价值。

不能报告：

- BARRED 整体方法错误。
- synthetic data 整体不可靠。
- debate agreement 等价于 truth。
- 当前 probes 覆盖真实世界全部 policy boundary。
- current anchor 等价于唯一真值；它只是实验中的授权参考。

## 论文路线分叉

### 路线 A：继续 Boundary Sufficiency

条件：

- clarified policy 明显降低 `policy_only_boundary_error_rate` 或 `boundary_instability_rate`。
- BARRED-like 前半段没有严重 pseudo-consensus，或 pseudo-consensus 只在 abstract policy 下出现、在 clarified policy 下减少。

论文主线：

> Boundary Sufficiency 是 policy specification testing：用 matched boundary probes 找到 abstract policy 的缺口，用 minimal clarification 验证缺口是否可修复，并在 synthetic data 之前检查 policy 是否足以指定要合成的边界。

适合写法：

- 不攻击 BARRED。
- 强调 preflight diagnostic。
- 把 clarified policy 作为正面结果：policy 写清楚有用，而我们的贡献是知道哪里没写清楚。

### 路线 B：转向 BARRED reliability audit

条件：

- BARRED-like 前半段出现稳定的 `pseudo_consensus_candidates`。
- `agreement` 高但 `anchor agreement` 低。
- clarified policy patch 能显著改变 judge/debate labels 或减少 pseudo-consensus。

论文主线：

> Synthetic/debate pipelines can produce high internal agreement on boundary interpretations that are not anchored in the current policy; policy sufficiency audit is needed before using these examples as training signal.

适合写法：

- 仍不 claim BARRED 错。
- 把对象限定为 BARRED-like synthetic/debate 前半段。
- 主张增加 reliability audit：`anchor agreement`、`policy_clause_support_rate`、`pseudo_consensus_candidates`。

### 路线 C：回退

条件：

- clarified policy 没有改善。
- BARRED-like 前半段没有 pseudo-consensus。
- abstract policy 条件下的 error/instability 在复跑中不稳定或消失。
- 主要失败来自 parse/format/prompt bug，而不是 substantive boundary behavior。

回退方向：

- 收窄为 prompt robustness / instruction following failure 分析。
- 改写为 negative result：当前小样本未能支持 policy boundary gap 主张。
- 只保留方法性贡献：如何构造 matched boundary probes 与如何避免 overclaim。

回退时不能硬撑：

- 不要把无 pseudo-consensus 写成 hidden risk。
- 不要把 clarified policy 无效写成 policy writing 无价值。
- 不要用低质量 generator 的失败批评 BARRED-like 方法。

## 最终判断模板

实验完成后，用以下短模板写结论：

```text
本轮结果对用户质疑的回应：

1. 对“policy 写清楚即可”的回应：
   - clarified policy 是否降低了 error/instability：
   - 若是：说明写清楚有用，Boundary Sufficiency 的价值是诊断哪里没写清楚。
   - 若否：说明当前失败可能不只是 wording，需要进一步区分 instruction following、policy-owner anchor 和 prompt robustness。

2. 对“BARRED 已经做 synthetic data”的回应：
   - BARRED-like 前半段的 sample yield：
   - agreement：
   - anchor agreement：
   - pseudo_consensus_candidates：
   - 若 high agreement / low anchor 出现：说明 debate agreement 需要 policy anchor audit。
   - 若没有出现：说明不能 claim BARRED-like pseudo-consensus，论文应回到 preflight diagnostic。

论文路线判断：
   - 继续 Boundary Sufficiency / 转向 BARRED reliability audit / 回退：
   - 理由：
   - 当前可以 claim：
   - 当前不能 claim：
```

## 执行检查清单

- 所有表格同时报告 absolute counts 和 rates。
- 所有 pseudo-consensus 判断都保留人工复核列。
- 所有 claim 都限定在当前 family、当前 prompts、当前 models。
- 单独记录 parse/format failure，不能混入 substantive error。
- 如果结果支持用户质疑，要正面承认，并把它转化为论文定位：我们的方法帮助发现何时需要写清楚、写清楚后是否真的有效。
