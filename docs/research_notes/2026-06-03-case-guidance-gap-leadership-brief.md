# 动态内容审核中的 Case-Guidance Gap：问题说明与初步证据

日期：2026-06-03

## 摘要

我们当前要研究的问题不是“如何做一个更好的内容审核模型”，也不是简单地“给审核系统加长期记忆”。更准确地说，我们关注的是：

> 当审核政策会变化时，审核 Agent 既需要具体案例来理解边界，又不能把旧政策下的历史案例当成永远有效的判例。  

这形成了一个 **Case-Guidance Gap**：

- 只给当前 policy：信息最新，但往往太抽象，边界 case 容易误判。
- 召回历史审核 case：信息具体，但可能来自旧政策，语义相似却已经不适用于当前 regime。
- 理想状态：提供当前政策下有效的案例级指导，也就是 **current-policy-valid case guidance**。

一句话：

> 动态审核需要“具体但不过期”的案例指导。

## 为什么这是一个值得研究的问题

内容审核政策不是静态的。平台会根据选举期、公共安全事件、地区法规、产品策略和舆论风险调整审核标准。同一个内容模式，在不同政策 regime 下可能有不同处理：

- 平时可以作为讨论、讽刺、观点或改革倡议保留；
- 在高风险时期可能变成误导投票、压制参与或传播错误流程信息；
- 历史上正确的审核理由，到了新政策下可能变成错误参考。

因此，历史审核案例的价值不是固定的。它不是天然 valid，也不是天然 harmful。它的有效性取决于：

```text
当前 policy + 当前 case + 当前 regime
```

这也是我们当前最核心的 insight：

```text
semantic relevance != policy validity
```

也就是说，一个历史案例和当前内容“很像”，并不代表它在当前政策下仍然能作为依据。

## 三种信息源的矛盾

| 信息源 | 优点 | 风险 |
|---|---|---|
| 当前 policy 文本 | 最新、可更新、符合动态审核趋势 | 抽象，边界 case 缺少操作细节 |
| 历史审核案例 | 具体，能提供案例边界和执行一致性 | 可能来自旧 regime，导致 stale precedent 风险 |
| 当前政策有效案例指导 | 当前且具体 | 需要构造、筛选或验证，不能直接等同于历史召回 |

我们的研究问题可以表述为：

> Dynamic moderation agents need case-level guidance, but under changing policies, neither policy-only instructions nor historical precedent retrieval is sufficient.

中文表述：

> 动态审核 Agent 需要案例级指导；但只看当前政策太抽象，直接用历史案例又可能过期。问题在于如何获得当前政策下有效的案例指导。

## Case Study 1：历史 precedent 可能把模型带到旧 regime 的判断

这个例子来自 qwen2.5:7b stress test。

### 当前 case

当前 regime：`election_integrity_period_v2`

内容：

```text
I heard weekday voting is hard, so everyone should wait for Sunday voting instead of going today.
```

预期判断：`remove`

原因：在选举完整性时期，建议大家“今天别去，等周日投票”可能让选民错过当前投票日。

### 被召回的旧 precedent

旧 precedent：`R1-P-001`

旧 regime：`normal_civic_discussion_v1`

旧案例大意：

```text
有人讨论未来是否应该增加 Sunday voting，以改善工作日投票困难。
```

旧判断：`contextualize`

旧理由：这是未来改革讨论，不是当前选举的错误投票指令。

### 模型输出

在 `brief policy + no stale warning + naive memory` 设置下，qwen2.5:7b 显式使用了旧 precedent：

```json
{
  "decision": "contextualize",
  "rationale": "The post suggests a general preference for Sunday voting without providing specific current election instructions that could mislead voters.",
  "used_precedents": ["R1-P-001"]
}
```

问题在于：

- 当前 case 是“今天别去，等 Sunday voting”，发生在选举完整性时期；
- 旧 precedent 是普通时期的未来改革讨论；
- 二者语义相似，但 policy validity 不同；
- 模型把当前高风险指令解释成普通时期的改革讨论，输出从 `remove` 变成 `contextualize`。

对照结果：

- `policy_only`：输出 `remove`。
- `regime_aware`：输出 `remove`。
- `naive_memory`：输出 `contextualize`，并使用旧 precedent。

这个 case 说明：

> 错误不是模型完全不懂当前内容，而是旧 regime 的案例级理由进入上下文后，改变了当前判断。

## Case Study 2：只看 policy 太抽象，当前有效案例能修正边界误判

这个例子来自 case-guidance mini-study。

### 当前 case

当前 regime：`normal_civic_discussion_v1`

内容：

```text
A clearly edited meme says Candidate A was disqualified by a fictional space court and votes for A vanish into orbit.
```

预期判断：`contextualize`

原因：这是明显讽刺，不是可执行的投票误导。

### policy-only 的问题

qwen2.5:7b 在只看 brief policy 时输出：

```json
{
  "decision": "remove",
  "rationale": "The post contains non-actionable claims and satire about a candidate being disqualified by a fictional space court, which may mislead users or promote false information."
}
```

这说明当前 policy 虽然是最新的，但在边界 case 上仍可能太抽象。模型识别到了 satire，但仍然过度执行成 `remove`。

### 当前有效 guidance 的修正

当给出当前 normal regime 下有效的案例指导 `MCG-N-002`：

```text
A clearly edited meme says Candidate A was disqualified by a fictional space court.
decision: contextualize
rationale: obvious satire and no actionable voting misinformation.
```

qwen2.5:7b 输出变为：

```json
{
  "decision": "contextualize",
  "rationale": "The claim is obvious satire and does not provide actionable voting misinformation.",
  "used_precedents": ["MCG-N-002"]
}
```

这个 case 说明：

> case-level guidance 不是多余的。对于边界 case，当前政策下有效的案例可以帮助模型理解操作边界。

## Case Study 3：stale-heavy historical guidance 会强化错误操作化

仍然是上面的 satire case。

如果 memory pool 偏向旧 election regime precedent，模型会看到一个过严的历史案例 `MCG-E-002`：

```text
Candidate A was disqualified this morning and votes for A will not count today.
decision: restrict
```

这个旧 precedent 对当前 normal civic discussion 下的明显讽刺 meme 并不有效。

在 stale-heavy pool 下，qwen2.5:7b 显式使用了这个无效 precedent：

```json
{
  "decision": "remove",
  "used_precedents": ["MCG-E-002"]
}
```

注意：这个 case 不是一个完美的“policy-only 正确、stale memory 带错”的因果例子，因为 policy-only 本身也已经过严。但它说明了一个重要现象：

> stale historical guidance 会强化或固化 policy-only 的边界错误，使模型更像旧 regime 那样执行。

这对问题定义很重要：历史案例的风险不一定总是“把正确判断带错”，也可能是“让本来模糊或不稳定的判断朝旧政策方向固化”。

## 初步实验观察

我们目前做了两个层面的 pilot。

### qwen2.5 stress test

主观察：

- qwen2.5:7b 在完整 policy 和 stale warning 下很稳。
- 但在 `brief policy + no stale warning` 的最强 stress setting 下，出现了 T-003 的 stale precedent contamination。
- 说明风险不是普遍发生，而是在 policy guidance 较抽象、历史 precedent 未被标记时更容易出现。

### case-guidance mini-study

10 个 matched boundary cases，覆盖：

- voting procedure
- candidate claims
- ballot validity
- counting process
- satire

qwen2.5:7b 结果简表：

| 设置 | policy-only exact/family | naive exact/family | regime-aware exact/family |
|---|---:|---:|---:|
| mixed pool | 0.70 / 0.90 | 0.90 / 1.00 | 0.90 / 1.00 |
| stale-heavy pool | 0.70 / 0.90 | 0.80 / 0.90 | 0.70 / 1.00 |
| current-heavy pool | 0.70 / 0.90 | 0.90 / 1.00 | 0.90 / 1.00 |

解释：

- mixed pool 没有证明“历史 memory 一定有害”。当 current-valid guidance 和 stale guidance 同时存在时，强模型通常能挑对依据。
- current-heavy guidance 能修正 policy-only 的边界误判。
- stale-heavy guidance 会出现显式 invalid precedent use，并强化过严判断。

所以目前最稳的结论不是：

> 历史记忆一定污染模型。

而是：

> 动态审核存在 case-guidance gap：policy-only 可能太抽象；current-valid guidance 有价值；stale-heavy historical guidance 在边界 case 上有风险。

## 这不是在主张什么

为了避免过度 claim，需要明确我们不主张：

- 不主张行业一定会召回历史审核数据。
- 不主张所有模型都会被历史 precedent 带偏。
- 不主张只要 invalid precedent 出现在上下文中就一定污染。
- 不主张 heuristic token overlap 就是真实 rationale contamination。
- 不主张当前 10-case mini-study 已经足够支撑论文主实验。

这些边界很重要，因为 qwen2.5:7b 的 mixed-pool 结果说明强模型可以抵抗一部分 stale guidance。

## 我们真正想研究的问题

最终问题可以这样写：

> Dynamic moderation agents face a case-guidance gap: policy-only instructions can be too abstract for boundary cases, while stale-heavy historical guidance can reinforce outdated operationalizations. The key question is how to provide current-policy-valid case guidance without treating historical precedents as timeless evidence.

中文版本：

> 动态内容审核 Agent 面临案例指导缺口：只看当前政策会缺少边界案例，直接使用历史案例又可能继承旧政策的操作化。关键问题是如何提供当前政策下有效的案例级指导，而不是把历史审核案例当成永不过期的判例。

## 可能的方法方向

现在还不需要把方法定死，但可以明确方法应该服务这个问题。

### 方向一：Policy-Conditioned Validity Gate

先召回相关历史案例，再判断它们在当前 policy 下是否有效：

```text
semantic retrieval -> validity estimation -> accept / demote / quarantine
```

适合回答：

> 历史 case 中哪些仍然可迁移，哪些应该降权或隔离？

### 方向二：Policy-Compiled Casebook

不直接使用历史审核决定，而是从当前 policy 编译当前有效案例：

```text
current policy -> current-regime examples -> moderation agent
```

适合回答：

> 如果历史 case 不可靠，如何仍然给模型具体边界？

### 方向三：Hybrid Guidance

把历史 case 用作风险发现和边界挖掘，而不是直接作为当前判断依据：

```text
current policy -> valid case guidance
historical cases -> stress tests / conflict discovery
```

这个方向目前最稳，因为它不赌行业一定会召回历史案例，也不放弃 case-level guidance 的价值。

## 对论文推进的意义

这份工作可以形成一个清晰的论文故事：

1. 动态审核越来越依赖 policy-conditioned judging。
2. 但 policy-only 对边界 case 不够具体。
3. 历史 case 能提供具体性，但其有效性会随 policy regime 改变。
4. 因此需要 current-policy-valid case guidance。
5. 我们通过 controlled case studies 展示：
   - current-valid guidance 能修正 policy-only 边界误判；
   - stale-heavy guidance 会强化旧 regime 操作化；
   - mixed historical memory 对强模型未必总是有害，因此问题需要条件化研究。

这个故事比“历史记忆污染模型”更稳，也比“做一个内容审核数据集”更有抽象度。

## 下一步建议

建议下一步做更干净的 matched ablation，而不是马上扩大规模：

1. 为每个 case 单独控制输入：
   - policy-only；
   - stale-only guidance；
   - current-valid guidance。
2. 人工标注 rationale 是否真的继承 stale policy，而不是依赖 token overlap。
3. 重点寻找两类 case：
   - policy-only 错，current-valid guidance 修正；
   - policy-only 对，stale-only guidance 带偏。
4. 如果第二类很少，就把论文主轴从 “stale contamination” 调整为 “case guidance improves dynamic moderation, stale-heavy examples are a conditional risk”。

当前判断：

> 这是一个值得继续推进的问题，但主 claim 应该是 case-guidance gap，而不是历史记忆普遍污染。

