# Dynamic Moderation 中的 Case-Guidance Gap：问题定义备忘

日期：2026-06-03

## 一句话问题

动态内容审核需要 case-level guidance，但当前政策文本往往太抽象，历史审核案例又可能因 policy regime 变化而失效。这个张力形成了一个 **case-guidance gap**：

> Moderation agents need concrete case-level guidance, but under changing policies, historical precedents are not timeless and policy-only instructions are often underspecified.

## 为什么要从 long-term memory 改写成 case-guidance gap

早期 framing 是：

> 长期审核 agent 会积累历史 precedent memory，因此需要 regime-aware memory management。

这个 framing 有一个部署假设：未来审核系统会召回历史审核数据作为当前判断依据。这个假设不够稳，因为如果审核政策频繁变化，行业很可能会避免直接依赖历史审核决定，以免旧政策边界污染当前执行。

更稳的 framing 是：

> 动态审核系统是否需要 case-level guidance？如果需要，它应该如何获得当前政策下有效的 case guidance，而不是直接复用旧历史 precedent？

这样，历史审核案例不再是我们必须“拯救”的对象，而是用来暴露问题的对照：

- 历史 case 具体，但可能 stale。
- 当前 policy 最新，但可能抽象。
- 真正需要的是 current-policy-valid case guidance。

## 核心张力

动态审核里存在三个信息源：

| 信息源 | 优点 | 风险 |
|---|---|---|
| Policy-only | 当前、可更新、符合动态政策趋势 | 规则抽象，边界 case 容易不稳定 |
| Historical precedents | 具体、可提供操作边界、提升一致性 | 可能来自旧 regime，语义相似但政策无效 |
| Current-policy-valid case guidance | 当前且具体 | 需要构造、验证或编译，不能简单召回 |

因此核心问题不是“要不要长期记忆”，而是：

> 在政策会变化的审核任务中，系统如何获得既具体又当前有效的 case-level guidance？

## 关键概念

**Policy regime**

某一时期或场景下实际执行的一组审核政策、优先级、例外和操作边界。它不只是 policy id，也包括政策强度、执行上下文和边界解释。

**Historical precedent**

过去某个 case 的审核决定、理由、申诉结果、训练示例或执行说明。它可以帮助当前判断，但它的有效性依赖产生它的 policy regime。

**Case-level guidance**

比抽象 policy 更具体的操作性指导，例如代表性案例、边界案例、反例、例外示例或 policy-derived exemplars。

**Policy-conditioned validity**

一条 case guidance 是否可以用于当前审核，取决于当前 policy、当前 case 和当前 regime，而不是取决于它与当前文本的语义相似度。

核心公式：

```text
semantic relevance != policy validity

validity = f(case_guidance, current_policy, current_case, current_regime)
```

## 研究问题

**RQ1: Policy-only insufficiency**

当只给当前 policy 和当前内容时，moderation agent 在边界 case 上是否表现出不稳定、过度执行或执行不足？

目的：证明 case-level guidance 有必要，而不是只用 runtime policy-conditioned judge 就足够。

**RQ2: Historical precedent risk**

语义相关但 policy-invalid 的历史 precedent 是否会导致 decision shift 或 rationale shift？

目的：证明直接召回历史 case 有风险。已有 pilot 中，llama3.2 出现 invalid precedent use；qwen2.5:7b 在最强 stress setting 的 T-003 中出现 explicit invalid precedent use 和 family-level decision harm。

**RQ3: Boundary conditions**

这种风险受哪些因素影响？

候选因素：

- policy specificity：完整政策 vs 高层政策摘要。
- stale-warning framing：是否提醒历史案例可能过期。
- model capability：强模型是否更能抵抗 stale precedent。
- case ambiguity：边界越模糊，是否越依赖 precedent。
- precedent similarity：无效 precedent 与当前 case 越像，是否越危险。

目的：把问题写成 robustness boundary，而不是单个 failure case。

**RQ4: Current-policy-valid guidance**

能否构造或筛选当前政策下有效的 case guidance，使 agent 同时获得具体操作边界，并避免历史 precedent 的 stale-regime contamination？

目的：为后续方法铺路，但当前 memo 不预设具体方法一定是 validity gate 还是 policy-compiled casebook。

## 当前 pilot 已经支持什么

现有 pilot 支持的是 seed-level evidence，不是论文级结论。

支持点：

1. **Historical precedent 有 utility**
   - qwen2.5:7b 在 operational setting 下，`naive_memory` 的 exact adherence 高于 `policy_only`。
   - 这说明 case-level guidance 可能有价值。

2. **Historical precedent 有风险**
   - llama3.2 在 operational setting 下，`naive_memory` 出现 invalid precedent use，并伴随 family-level adherence 下降。
   - qwen2.5:7b 在 `brief policy + stale warning off` 的 T-003 中显式使用无效旧 precedent `R1-P-001`，把 expected `remove` 输出成 `contextualize`。

3. **风险有条件**
   - qwen2.5:7b 在主 operational setting 下很稳。
   - qwen2.5:7b 的污染只在更强 stress setting 下出现。
   - 因此不能 claim “强模型普遍会被历史 precedent 污染”，只能 claim “在 policy guidance 较抽象且历史 precedent 未被标记时，风险会出现”。

4. **Regime-aware / policy-valid guidance 有潜在缓解价值**
   - 在 T-003 中，`policy_only` 和 `regime_aware` 都能输出正确 family，而 `naive_memory` 错。
   - 这说明问题来自无效旧 precedent 进入上下文，而不是模型完全不会处理该 case。

## 当前 pilot 没有证明什么

不能证明：

- 行业一定会召回历史审核 case。
- 所有模型都会被 stale precedent 污染。
- heuristic overlap 等于 rationale contamination。
- simple regime-id filtering 就是最终方法。
- policy-compiled casebook 一定优于 validity gate。
- 10-case pilot 足以支撑论文主实验结论。

这些都必须在后续实验或论文表述中严格限制。

## 可行的论文主张

当前最稳的论文主张应写成：

> Dynamic moderation agents face a case-guidance gap: policy-only instructions are current but often underspecified, while historical precedents are concrete but can become invalid under policy changes. We study when historical case guidance helps or harms, and how current-policy-valid guidance can reduce this utility-risk tradeoff.

更短版本：

> Under changing moderation policies, case-level guidance must be conditioned on current policy validity, not merely semantic relevance.

## 不建议的主张

不建议写：

- “大厂审核系统会召回历史数据。”
- “长期历史审核记忆是未来审核 agent 的必然方向。”
- “我们证明强模型会被 stale precedent 污染。”
- “regime-aware memory 一定优于 policy-only。”
- “stale rationale heuristic 是污染真值。”

这些说法要么依赖部署假设，要么超出 pilot 证据。

## 方法空间

问题明确后，方法可以有三种路线。当前不需要马上定死，但可以比较：

### 方法路线 A：Policy-Conditioned Validity Gate

流程：

```text
semantic retrieval -> validity estimation -> accept / demote / quarantine -> moderation agent
```

优点：

- 延续现有 pilot。
- 直接解决 stale historical precedent。
- 容易和 naive memory、regime-id filter、oracle filter 做对照。

风险：

- 如果只用显式 regime id，就像 metadata filtering。
- 必须展示它能处理 regime label 缺失、policy diff、rationale conflict 或 transferable precedent。

### 方法路线 B：Policy-Compiled Casebook

流程：

```text
current policy -> compile current-regime examples -> use casebook as guidance
```

优点：

- 符合“动态审核不应直接依赖旧历史 case”的行业直觉。
- 方法感强，像从当前 policy 编译 operational guidance。
- 可以把历史 case 降级为 boundary discovery / test generation，而不是 prompt evidence。

风险：

- 会引入 casebook 维护与存储负担。
- 如果只是生成 few-shot examples，容易被质疑为 prompt engineering。
- 需要证明 compiled casebook 比 policy-only 更稳，比 historical memory 更安全。

### 方法路线 C：Hybrid Guidance

流程：

```text
current policy -> generated/compiled examples
historical cases -> only for conflict discovery and stress testing
valid historical cases -> optionally promoted after validation
```

优点：

- 最符合当前讨论：不赌行业直接召回历史 case，也不放弃 case-level guidance。
- 可以把历史 precedent 从“记忆依据”改成“风险检测材料”。
- 方法可以自然包含 validity gate 和 policy-compiled casebook。

风险：

- 范围容易变大。
- 需要清晰拆分主方法和附加模块。

## 当前推荐

当前推荐把论文问题定为：

> The Case-Guidance Gap in Dynamic Moderation

方法先暂称：

> Policy-Conditioned Case Guidance

不要立即定死是 validity gate 还是 policy-compiled casebook。后续小实验应回答：

1. policy-only 是否真的在边界 case 上不够？
2. historical memory 是否真的在 matched cases 上有稳定污染风险？
3. current-policy-valid guidance 是否能同时提升具体性和安全性？

如果 1 和 2 都成立，再选择方法路线：

- 如果 historical memory 的风险强、但有些历史 case 可迁移：走 validity gate。
- 如果 policy-only 不足明显、历史 case 风险也明显：走 policy-compiled / hybrid guidance。
- 如果 historical risk 很弱：转向 policy ambiguity / operationalization sensitivity，而不是 memory paper。

## 下一步建议

不要马上扩成 60-100 case，也不要继续堆模型。下一步应做一个问题确认 mini-study：

1. 设计 8-12 个 matched boundary cases。
2. 每个 case 都有：
   - policy-only setting；
   - naive historical memory setting；
   - current-policy-valid guidance setting。
3. 手工标注：
   - decision correctness；
   - family correctness；
   - 是否使用 invalid precedent；
   - 是否出现人工确认的 stale rationale contamination。
4. 目标不是跑大表，而是确认 case-guidance gap 是否稳定存在。

通过标准：

- policy-only 至少在部分边界 case 上不稳定或缺少具体性；
- naive historical memory 至少在多个 matched case 上出现 stale precedent risk；
- current-policy-valid guidance 能降低风险，同时不牺牲太多 utility。

如果这个 mini-study 成立，再进入正式方法和主实验设计。

