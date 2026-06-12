# Regime-aware Moderation Memory Pilot 设计规格

日期：2026-06-01

工作标题：**Precedents Are Not Policies: Regime-Aware Memory for Long-Term Moderation Agents**

## 1. 目标

这个 pilot 的目标，是验证长期内容审核 agent 是否需要 regime-aware 的 precedent memory。

`claudecode.result` 里的旧 pilot 主要测试的是：在新 policy 被显式写进 system prompt 之后，旧记忆是否还会诱导 agent 违反新 policy。这个设定后来信号变弱，因为评估方式修正后，强模型往往能遵守当前 prompt 并忽略旧记忆。

v2 pilot 要测试一个更适合论文的问题：

> 历史审核 precedent 在产生它的 policy regime 内是有用的，但当 policy regime 改变后，它可能失效。一个好的长期审核记忆系统，应当保留同 regime precedent 的一致性收益，同时抑制跨 regime 的 precedent 污染。

因此，pilot 必须同时测 **utility** 和 **risk**。如果 memory 只有风险，结论会变成“不要用记忆”；如果 memory 只有收益而没有污染，那么 regime-aware 机制没有必要性。我们需要看到 tradeoff，并证明 regime-aware memory 能改善这个 tradeoff。

## 2. 研究问题

**RQ1：同 regime 记忆收益。** precedent memory 是否能提高同一 policy regime 下边界审核案例的一致性？

**RQ2：跨 regime 污染。** 当 policy regime 改变时，naive semantic retrieval 是否会激活语义相关但 regime-invalid 的历史 precedent？

**RQ3：regime-aware 缓解。** regime-aware memory 是否能在保留同 regime 一致性收益的同时，降低 invalid precedent activation 和 stale rationale？

## 3. 推荐范围

第一轮 pilot 只做一个主域：

**Election and civic misinformation moderation。**

这个域适合作为起点，因为审核政策会自然随 regime 改变，尤其是普通公共讨论期和选举完整性保护期之间。相似帖子在不同 regime 下可能有不同正确处理方式，因此 conflict pairs 比较容易检查。

第一轮不要扩展到太多域。等信号成立后，再考虑加入 harassment、crisis-event misinformation、health misinformation 或平台特定规则作为补充实验。

## 4. Regime 设置

### R1：Normal Civic Discussion

政策姿态：

- 一般政治观点通常允许。
- 讽刺和评论通常允许，除非造成直接操作性伤害。
- 关于政治人物的未经证实说法，可以 contextualize，而不一定 remove。
- 投票程序类说法若包含操作性指令需要 review，但普通讨论期整体更宽松。

示例决策：

- 关于候选人的讽刺 meme：`allow` 或 `contextualize`。
- 笼统声称候选人腐败：`allow` 或 `contextualize`。
- 非操作性的竞选策略传闻：`allow` 或 `contextualize`。

### R2：Election Integrity Period

政策姿态：

- 错误或未经证实的投票程序信息应 `restrict` 或 `remove`。
- 关于候选人资格、选票有效性、投票时间、投票地点、计票流程的误导性内容应 `escalate`。
- 讽刺仍可保护，但必须清楚不具欺骗性。
- 选举完整性窗口内，边界 civic claims 应更严格处理。

示例决策：

- “投票不是今天结束，而是明天结束”：若错误或未经证实，`remove`。
- “X 选区的邮寄选票不会被计算”：`remove` 或 `escalate`。
- 临近选举日的候选人资格谣言：`restrict` 或 `escalate`。

## 5. 数据模型

每条 memory 应保存为结构化 precedent record，而不是普通文本块。

```json
{
  "case_id": "R1-P-004",
  "regime_id": "normal_civic_discussion_v1",
  "policy_rule": "candidate_claims",
  "post": "A sarcastic meme claims Candidate A is secretly disqualified.",
  "decision": "contextualize",
  "rationale": "The post is framed as satire and does not provide actionable voting misinformation.",
  "validity_scope": "Valid under normal civic discussion rules; not automatically valid during election-integrity periods.",
  "exception_tags": ["satire", "candidate_claim"],
  "superseded_by": null
}
```

推荐决策标签：

- `allow`
- `contextualize`
- `restrict`
- `remove`
- `escalate`

推荐字段：

- `case_id`
- `regime_id`
- `policy_version`
- `policy_rule`
- `post`
- `decision`
- `rationale`
- `validity_scope`
- `exception_tags`
- `superseded_by`
- `compatible_regimes`

## 6. 测试案例类型

### A. Within-Regime Holdout

这些是 R1 下的新案例，与 R1 precedents 相似但不是重复样本。

目的：

- 测试 memory 是否提高同 regime 一致性。
- 证明 precedent memory 有正向价值，而不只是风险来源。

预期：

- `Policy Only` 在模糊案例上可能不稳定。
- `Naive Memory` 应提高一致性。
- `Regime-Aware Memory` 应接近或匹配 `Naive Memory` 的同 regime 收益。

### B. Cross-Regime Conflict Pairs

这些案例与 R1 precedents 语义相近，但在 R2 下应给出不同处理。

目的：

- 测试 semantic retrieval 是否会检索错误 precedent。
- 证明 precedent 可以“相关但无效”。

预期：

- `Naive Memory` 会检索 R1 precedent 并过度套用。
- `Regime-Aware Memory` 会抑制或降低 R1-only precedent 的权重。

### C. Boundary Ambiguity

这些案例中，当前 policy 文本本身可能不足以稳定给出处理方式，但同 regime precedent 可以澄清边界。

目的：

- 避免实验对 `Policy Only` 太简单。
- 更接近真实审核流程：policy text 和 precedent 共同塑造一致决策。

预期：

- 同 regime precedent 提高 rationale 和 label 一致性。
- 跨 regime precedent 造成 stale rationale error。

## 7. 实验条件

### 1. Policy Only

agent 只看到当前 policy regime 和待审核内容。

这是测试 memory 是否有增益的 baseline。

### 2. Naive Memory

agent 只按语义相似度检索 top-k precedents。

这是容易失败的 memory baseline。它应在 R1 holdout 中检索有用案例，但也可能在 R2 中检索 invalid R1 precedent。

### 3. Regime-Filtered Memory

agent 只检索当前 `regime_id` 下的 precedent。

这是强诊断 baseline。如果 regime 显式且标签可靠，它可能表现很好。论文中必须认真对待它，不能把它写成 strawman。

### 4. Regime-Aware Memory

agent 检索当前 regime precedent，以及被标记为 invariant 或 compatible 的 memories；同时抑制 validity scope 与当前 regime 冲突的 memory。

第一版可以用 metadata hard eligibility 实现。后续版本再加入 learned compatibility judgment、policy-diff reasoning 或 memory lifecycle actions。

## 8. 指标

### Policy Adherence

最终决策是否符合 active regime 下的 expected decision。

### Within-Regime Consistency Gain

在 same-regime holdout 和 boundary cases 上，相比 `Policy Only` 的提升。

### Invalid Precedent Activation

top-k retrieved memories 中，有多少在 active regime 下无效。

### Cross-Regime Contamination Rate

回答的 decision 或 rationale 是否沿用了 incompatible regime 的 precedent。

### Stale Rationale Rate

回答理由是否使用了旧 regime 下成立、当前 regime 下不成立的逻辑。

### Utility-Risk Tradeoff

可作为摘要指标：

```text
within_regime_gain - cross_regime_contamination
```

论文中可以用它帮助叙事，但必须分别报告各个子指标。

## 9. 最小 pilot 规模

第一版可执行 pilot：

- 2 个 regimes。
- 40 条 construction precedents。
- 60 条 test cases。
- 3 或 4 个实验条件。
- top-k retrieval，`k = 3` 或 `k = 5`。
- 结构化输出：decision label + short rationale。

建议拆分：

- 20 条 R1 construction precedents。
- 20 条 R2 construction precedents。
- 20 条 R1 within-regime holdout tests。
- 20 条 R2 conflict-pair tests。
- 20 条 ambiguity/boundary tests。

## 10. 评估

旧 pilot 证明关键词匹配会产生 false positives。v2 pilot 应使用结构化输出，并搭配 LM judge 或人工抽查。

agent 输出格式：

```json
{
  "decision": "remove",
  "rationale": "The post gives false information about voting time during the election-integrity period.",
  "used_precedents": ["R2-P-011"]
}
```

judge 任务：

- decision 在 active regime 下是否正确？
- 回答是否依赖 invalid precedent？
- rationale 是否 stale，即引用了旧 regime 逻辑？
- 被引用 precedents 是否与 active regime compatible？

第一轮 pilot 建议人工检查一个小子集，用来校准 LM judge。

## 11. 成功标准

如果 pilot 同时显示以下三点，就继续推进：

1. `Naive Memory` 相比 `Policy Only` 提高 within-regime consistency。
2. `Naive Memory` 在 regime shift 下增加 invalid activation 或 contamination。
3. `Regime-Aware Memory` 保留大部分 within-regime benefit，同时降低 contamination。

如果出现以下情况，暂停或 pivot：

- memory 不提高 same-regime decisions。
- naive memory 不产生可测量的 cross-regime contamination。
- regime-aware memory 在所有设置下都不优于 simple regime filtering。

若最后一点发生，论文应转为 evaluation/phenomenon paper，或者强化方法，使它不仅是 metadata filtering。

## 12. 预期论文贡献

这个 pilot 用来支撑以下贡献表述：

1. 内容审核 memory 存在 precedent-validity problem：语义相关 precedent 不一定是 policy-valid precedent。
2. 现有 dynamic policy judging 系统不能解决长期 precedent lifecycle management。
3. regime-aware memory 应用 utility-risk tradeoff 评估，而不是只看 retrieval accuracy 或 final decision accuracy。
4. 一个可控 moderation pilot 可以揭示 memory 什么时候有用、什么时候污染、regime-aware retrieval 什么时候改善 tradeoff。

## 13. 与已有工作的关系

### DynaGuard

DynaGuard 根据当前用户定义 policy 条件化 guardian model。它相关，但不覆盖本 pilot，因为它不研究长期 precedent memory、memory validity 或 stale precedent activation。

### STITCH / STALE / GLOVE / CMI

这些工作是重要压力，因为它们研究 contextual intent、stale memory、memory-environment mismatch 或 causal memory selection。我们的区分点应放在 moderation-specific structure：

- policy regimes；
- precedents；
- policy versioning；
- appeal-like consistency；
- stale rationale；
- rule hierarchy and exceptions；
- content moderation decision labels。

### GMP / RuleSafe-VL / Policy-as-Prompt

这些工作约束 moderation 侧。我们不能把本文写成“又一个审核数据集”或“又一个规则 prompt”。新意应落在 changing moderation regimes 下的 long-term precedent memory。

## 14. 实现计划预览

下一步实现计划应创建：

- `pilot/data/policies.json`
- `pilot/data/precedents.jsonl`
- `pilot/data/test_cases.jsonl`
- `pilot/src/retrieval.py`
- `pilot/src/conditions.py`
- `pilot/src/evaluate.py`
- `pilot/src/run_pilot.py`
- `pilot/results/`

第一版可用透明 vector store，甚至先用 embedding similarity over JSONL records。不要第一步使用 Mem0，因为旧 Claude run 发现 extraction 不稳定且可能 silent failure。

## 15. 第一周 checklist

1. 手写 policy regimes 和 10 条 sample precedents。
2. 建立 JSONL schema 和 validation script。
3. 实现三个条件：`Policy Only`、`Naive Memory`、`Regime-Aware Memory`。
4. 先在 10 条案例上运行，检查 prompt 和 output。
5. 加入 LM judge 和人工校准。
6. 扩展到 60 条 test cases。
7. 产出第一张 result table 和 error analysis。
