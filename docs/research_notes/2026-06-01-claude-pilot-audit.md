# Claude 旧 Pilot 审计

日期：2026-06-01

来源：`claudecode.result`

## 摘要

Claude 之前帮助做的 pilot 有价值，但它不是当前 Regime-aware Moderation Memory 方向真正需要的 pilot。

旧 pilot 主要测试的是：在 policy shift 被显式写入 prompt 后，旧 memory 是否会导致错误。早期关键词评估看起来有正信号，但换成 LM evaluator 后，结果明显变弱甚至消失。这个结果不说明方向死亡，而说明旧实验设计测错了问题。

## 旧 Pilot 测了什么

旧 pilot 使用了以下类型的 scenario：

- customer service policy shift；
- content moderation policy shift；
- sales goal shift；
- communication norm shift。

大致流程是：

1. 在 Regime A 下构造 memories。
2. 用显式 system prompt 切换到 Regime B。
3. 比较 no-memory、raw-memory、MVG-filtered memory。
4. 检查 raw memory 是否导致 Regime A 行为出现在 Regime B 下。

这测的是 cross-regime harm，但没有充分测试 within-regime memory utility。

## 关键发现

### 1. Mem0 对当前 pilot 不稳定

旧实验中，Mem0 extraction 出现空结果或不可靠结果。直接 vector-store 方法更透明、更可复现。

设计含义：

> v2 先使用透明 memory store，不要从 Mem0 开始。

### 2. 关键词匹配会产生 false positives

旧 pilot 曾因为回答里出现 “refund” 或 “discount” 就判为失败，即使模型是在拒绝退款或拒绝折扣。

设计含义：

> 使用结构化 decision label，加 LM judge 或人工抽查。不要把关键词匹配作为主评估器。

### 3. 显式 policy prompt 会让强模型天然 robust

当当前 regime 在 system prompt 中写得很清楚时，强模型往往能遵守它并忽略 stale memory。旧实验的完整 LM-evaluated run 中出现了 0% memory-induced error。

设计含义：

> v2 不能依赖“旧 memory 总会覆盖显式 policy”这个简单假设。它应该测试 precedent utility 和 boundary-case consistency。

### 4. 旧 pilot 测了风险，但没有证明收益

旧实验重点在于 memory 是否会在 regime change 后有害，但没有充分证明 precedent memory 会提升同 regime 审核一致性。

设计含义：

> v2 必须包含 same-regime holdout cases，证明 memory 有用。

## 为什么这不否定当前选题

旧 negative result 与新方向并不冲突。它说明：

> 如果当前 policy 显式且完整，强模型可能不需要旧 memory，也可能忽略 invalid precedent。

当前假设不同：

> 在内容审核中，policy text 经常不足以完全决定边界案例。precedents 可以提升同 regime 一致性，但这些 precedents 必须被 scope，因为它们跨 regime 后可能失效。

这个假设更强，也更接近真实审核流程。

## 可复用部分

可以复用：

- phase-based construction/query structure；
- no-memory vs raw-memory vs filtered-memory 对比；
- LM judge 思路；
- transparent vector-store baseline；
- retrieved memories 和 final decisions 的日志记录。

不要原样复用：

- keyword evaluator；
- Mem0-first implementation；
- 只测试显式 regime shift 后 instruction-following 的 scenario；
- 把 memory 只写成有害因素的 framing。

## v2 Pilot 的核心教训

新 pilot 应围绕这句话设计：

> 审核 precedent 不只是语义相关证据；它只在特定 policy regime 下有效。
