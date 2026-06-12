# Policy-to-Operation Gap 论文推进方向

日期：2026-06-09

## 一句话结论

我们当前最好的论文方向不是“再做一个内容审核模型”，也不是“把审核规则写成决策树”，而是：

> 提出一种面向 LLM 内容审核的 **policy specification testing methodology**，用于发现自然语言审核政策在走向真实部署时仍然存在的 **policy-to-operation specification gap**。

换句话说，我们研究的问题是：

```text
high-level policy / platform intent
        -> operational moderation decision
        -> allow / contextualize / restrict / remove / escalate
```

中间是否存在未被充分规定的边界变量和动作阈值。

## 核心问题定义

真实内容审核系统需要输出稳定的可执行动作，而平台或用户给出的 policy 通常是高层、抽象、自然语言形式的。这个 gap 不是简单的“模型不够强”，也不是简单的“规则没写清楚”常识，而是一个可以测试的问题：

> 当前 policy 是否足以支持稳定、可部署、可复核的 moderation operation？

我们把这个缺口称为 **policy-to-operation specification gap**。它至少包含两层：

1. **Boundary sufficiency**

   Policy 是否足以规定什么情况触发审核边界。

   例如：
   - future reform discussion vs current voting instruction
   - obvious satire vs deceptive official-looking notice
   - prediction/opinion vs false certification
   - education/critique quote vs endorsement/mobilization

2. **Action-granularity sufficiency**

   Policy 是否足以规定触发边界之后应采取哪种具体动作。

   例如：
   - debunking false claim + official source -> allow 还是 contextualize？
   - critique without official source -> allow 还是 contextualize？
   - quote plus endorsement -> remove 还是 escalate？
   - mobilization to suppress participation -> remove 还是 escalate？

这里 `endorsement`、`mobilization`、`satire`、`official source` 不是动作，而是决定动作的 **boundary variables**。真正的动作是：

```text
allow / contextualize / restrict / remove / escalate
```

因此，我们的主张不是“用动作替代规则”，而是：

> boundary/action 是观察和定位 policy gap 的坐标系；minimal clarification 是验证 gap 是否可被修复的手段。

## 和“写决策树”的区别

一个足够可执行的 policy 最终当然可能表现得像决策树。但我们的研究对象不是手工写出这棵树，而是诊断自然语言 policy 是否已经足以支撑这棵树。

更准确地说：

```text
不是：我们帮平台写完整规则树。
而是：我们测试现有 policy 的隐式决策树在哪里缺分支、缺动作阈值、或被模型/历史案例/合成数据擅自补全。
```

这也是学术贡献所在：把 policy 从“给定的自然语言 prompt”变成“需要被测试的 specification”。

## 方法定位

我们提出 **boundary/action probing**，作为 policy specification testing 的具体方法。

它包含三步：

1. **探索 gap**

   构造成对 matched probes，只改变一个候选 boundary variable，观察模型的判断是否发生预期变化。

2. **表征 gap**

   把输出映射到 action space，区分两种错误：
   - coarse decision-family error：是否该干预都错了；
   - exact action error：知道该不该干预，但具体动作不稳定。

3. **验证 gap**

   加入 minimal clarification，测试错误率和 action instability 是否下降。

如果澄清边界之后只降低 decision-family error，而 action label 仍然不稳定，就说明 action-granularity 是独立层次。若再加入 action rubric 后 exact-action error 下降，就能支持论文主张。

## 当前 pilot 证据

已有结果已经给出可推进信号。

### Boundary sufficiency 主结果

主 12-case pilot 中：

| 指标 | 结果 |
|---|---:|
| `policy_only_boundary_error_rate` | 0.479 |
| `current_guidance_rescue_rate` | 1.000 |
| `stale_guidance_harm_rate` | 0.833 |
| `boundary_instability_rate` | 0.750 |
| `invalid_used_precedent_rate` | 0.049 |

解释：

- policy-only 在多个 family 上出现边界不稳定；
- current-policy-valid guidance 可以 rescue；
- stale/data-first guidance 会造成 harm；
- 这支持 “policy 本身是否足够可执行” 是可观测问题。

### Clarified policy 对照

12-case clarified policy 对照中：

| 条件 | policy-only error | instability |
|---|---:|---:|
| abstract | 0.500 | 0.667 |
| clarified | 0.250 | 0.333 |

解释：

- 写清楚 policy 确实有用；
- 我们的价值不是否认 policy clarification，而是诊断哪里需要 clarification。

### Action-granularity 信号

education extended 中更关键：

| 条件 | overall exact error | overall family error | education exact error | education family error |
|---|---:|---:|---:|---:|
| abstract | 0.4375 | 0.2188 | 0.3571 | 0.1429 |
| clarified | 0.3438 | 0.0000 | 0.6429 | 0.0000 |

解释：

- clarified policy 把 coarse decision-family 修到了 0；
- 但 exact action label 在 education family 上反而更不稳定；
- 这说明 policy 可以足以规定“是否干预”，但不足以规定 “allow/contextualize/remove/escalate 的具体动作粒度”。

这是当前最强的论文动机。

## 相关工作定位

### Policy-as-Prompt

Policy-as-Prompt 讨论了 LLM 时代内容审核从传统 “policy -> operational guideline -> label/training” 转向 “policy 直接作为 prompt” 的趋势。

我们的关系：

- 它说明了 policy 直接进入模型执行的范式；
- 我们进一步问：policy 作为 prompt 之前，是否已经足以支持 operational decision？

URL: https://arxiv.org/abs/2502.18695

### DynaGuard

DynaGuard 代表 runtime policy-conditioned judging：给定当前 policy 和当前内容，模型直接判断是否违规。

我们的关系：

- DynaGuard 关注 “给定 policy 后如何执行”；
- 我们关注 “给定 policy 是否足以被执行”。

URL: https://arxiv.org/abs/2509.02563

### BARRED

BARRED 代表 custom guardrails / synthetic data 路线：给定 task/policy，通过 synthetic boundary examples 和 debate 生成训练数据，再训练 guardrail。

我们的关系：

- BARRED 关注如何低成本生成和筛选训练数据；
- 我们关注生成数据之前，source policy 是否已经足以规定要生成的边界；
- 我们不 claim BARRED 错，而是 claim synthetic/debate pipeline 需要 policy sufficiency preflight。

URL: https://arxiv.org/abs/2604.25203

### Content Moderation for Evolving Policies using Binary QA

该工作把 evolving moderation policy 拆成 binary QA themes，再组合决策。

我们的关系：

- 它把 policy operationalization 变成 QA 分解；
- 我们不是把 policy 固定拆成 QA，而是用 probes 检测哪些 boundary variables/action thresholds 尚未充分规定。

URL: https://aclanthology.org/2023.acl-industry.54/

### HateModerate / GuardBench / GuardSet-X / GSPR

这些工作从 benchmark、policy-grounded evaluation 或 general safety reasoning 角度接近我们的主题。

我们的关系：

- HateModerate 更接近 policy conformance testing，检查模型是否符合特定平台 hate policy；
- GuardBench 和 GuardSet-X 更偏安全评测集合、policy-grounded guardrail data 或多领域 benchmark；
- GSPR 更接近 generalizable safety policy reasoning；
- 它们强化了一个压力点：不能只说“我们也测试 policy”，必须强调我们测试的是 **policy operationalization 的规格充分性**，尤其是 boundary variables 与 action granularity 是否足以支撑真实动作。

可引用 URL：

- HateModerate: https://aclanthology.org/2024.findings-naacl.172/
- GuardBench: https://aclanthology.org/2024.emnlp-main.1022/
- GuardSet-X: https://openreview.net/forum?id=mORzRZaqT4
- GSPR: https://arxiv.org/abs/2509.24418

### Trust & Safety 行业实践

TSPA 等行业材料强调 moderator 需要 enforcement guideline、decision tree、action choice、escalation path。

我们的关系：

- 行业上确实需要把 high-level policy 变成可执行动作；
- 我们的贡献不是重复这个流程，而是提出可测试的方法，发现 policy 在进入这个流程之前哪里还不足。

URL: https://www.tspa.org/curriculum/ts-fundamentals/content-moderation-and-operations/setting-up-a-content-moderator-for-success/

## 推荐论文标题

首选：

> **From Policy to Operation: Probing Specification Gaps in LLM Content Moderation**

备选：

> **Policy-to-Operation Gaps in LLM Content Moderation**

> **Testing Policy Sufficiency for LLM-Based Moderation**

> **Boundary and Action-Granularity Sufficiency in Policy-Conditioned Moderation**

## 贡献表述

建议贡献写成四条：

1. We introduce **policy-to-operation specification gap**, a failure mode where natural-language moderation policies do not fully specify the boundary variables and enforcement actions required for stable deployment.

2. We decompose this gap into **boundary sufficiency** and **action-granularity sufficiency**, showing that a policy may support coarse intervention decisions while remaining insufficient for exact moderation actions.

3. We propose **boundary/action probing**, a policy specification testing method that uses matched probes, action-space analysis, and minimal clarification tests to localize underspecified policy regions.

4. We demonstrate through pilot studies that current-valid clarification can reduce boundary errors, stale/data-first guidance can induce harmful shifts, and action-level gaps can persist even after coarse boundaries are clarified.

## 最小实验路线

下一步不要扩成大 benchmark。最小验证应围绕 “boundary guidance 修 family，action rubric 修 exact action” 展开。

### E1: Boundary sufficiency replication

目的：确认已有 12-case 结果不是偶然。

条件：

- P0: abstract policy
- P1: boundary-clarified policy
- P3: stale/misaligned guidance

指标：

- decision-family error
- rescue rate
- stale harm rate
- instability

预期：

- P1 降低 family-level error；
- P3 增加 harm 或 instability。

### E2: Action-granularity experiment

目的：验证 action gap 是独立层次。

条件：

- P1: boundary-clarified policy
- P2: boundary-clarified + action rubric

case family：

- education/critique quote vs endorsement/mobilization
- allow vs contextualize
- remove vs escalate
- contextualize vs remove

指标：

- exact action error
- decision-family error
- action instability

预期：

- P1 下 family error 低，但 exact action error 高；
- P2 降低 exact action error；
- 这会证明 action-granularity sufficiency 不等于 boundary sufficiency。

### E3: Boundary/action separation 2x2

目的：最清晰地区分两个 gap。

矩阵：

| 条件 | boundary guidance | action guidance |
|---|---|---|
| C0 | absent | absent |
| C1 | present | absent |
| C2 | absent | present |
| C3 | present | present |

预期：

- C1 主要修 decision-family error；
- C3 进一步修 exact-action error；
- C2 如果没有 boundary guidance，action guidance 可能无法完全发挥作用。

## 暂缓事项

当前不要做：

- 大规模多领域数据集；
- 大量模型横评；
- 复杂 prompt ablation；
- 完整 BARRED 复现和 fine-tuning；
- 大规模人工标注；
- 真实平台 policy 全量复刻。

这些会把论文拖回工程 benchmark，而不是机制验证。

## 支持或削弱方向的结果

支持：

- boundary clarification 降低 decision-family error；
- action rubric 在 family 已经正确时继续降低 exact-action error；
- stale guidance 引入可观测 harm；
- 不同模型方向一致；
- mixed cases 显示 boundary 信息和 action 信息影响不同指标。

削弱：

- boundary clarification 同时完全修好 exact action，说明 action gap 可能不独立；
- action rubric 对 exact-action error 无增益；
- 人类对 action label 本身高度不一致；
- 不同模型效应方向完全相反；
- 错误主要来自 parse/prompt 格式，而非实体判断。

## 写作边界

可以 claim：

- policy sufficiency 是 LLM moderation 的前置诊断问题；
- boundary/action probing 可以定位未充分规定的 policy region；
- minimal clarification rescue 是强诊断证据；
- 当前 pilot 支持继续扩展为正式 study。

不能 claim：

- 我们自动恢复 true policy；
- 我们替 policy owner 做最终价值判断；
- BARRED 或 DynaGuard 错；
- synthetic data 没有价值；
- 所有 moderation failure 都来自 policy underspecification；
- 当前 12/16-case pilot 足以成为最终论文实验。

## 推荐下一步

1. 先写论文骨架：abstract、introduction、related work positioning、method overview。
2. 再做 action-granularity 8-12 case 小实验。
3. 增加 analyzer 的 exact action vs decision-family metrics。
4. 用 2 个模型先跑，不做大规模。
5. 若 E2/E3 信号成立，再扩成正式 study。

当前方向值得推进。它的学术 taste 在于：我们不是做“更好的审核器”，而是提出一个前置的 specification testing layer，用于测试 high-level policy 是否足以支撑 operational moderation。
