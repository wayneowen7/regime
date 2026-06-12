# 自动化 Policy-to-Operation Specification Testing 方法设计

日期：2026-06-11

## 一句话定位

我们不把当前工作写成“手工构造 12 条 probes 的 pilot”，而是提升为一个自动化诊断方法：

> 给定一份高层自然语言审核 policy，自动发现它在走向真实 moderation action 时可能缺失的边界变量和动作阈值，生成 matched boundary/action probes 进行测试，并输出最小澄清建议与证据报告。

这个方法可以暂命名为：

> **AutoBAP**：Automated Boundary-Action Probing for LLM Moderation

或者更论文风格：

> **BoundaryProbe**：Diagnosing Operational Sufficiency of Moderation Policies

本文档先用 `AutoBAP` 表示。`BoundaryProbe` 更适合作为论文标题或系统别名；`AutoBAP` 更适合放在 Method section 里，因为它明确包含 boundary 与 action 两层。

## 为什么这不是“又在写规则”

一个足够完整的 operational policy 最终当然可能表现得像决策树。但我们的目标不是替平台手写整棵树，而是测试现有自然语言 policy 是否已经足以支撑这棵树。

区别是：

```text
规则工程：
  人工把 policy 写成完整决策树。

AutoBAP：
  自动测试自然语言 policy 的隐式决策树在哪里缺分支、缺阈值、缺动作映射，
  并用最小 probes 和最小 clarification 证明这些缺口会改变模型决策。
```

因此方法的核心不是“把规则写清楚”，而是：

1. 自动提出候选边界变量；
2. 自动构造只改变一个变量的 matched probes；
3. 自动运行多模型、多 policy view 诊断；
4. 自动定位 gap 属于 boundary insufficiency 还是 action-granularity insufficiency；
5. 自动生成最小澄清建议，并用 before/after rescue 验证它是否真的修复决策。

## 输入与输出

### 输入

`AutoBAP` 的输入包括：

- `P`: 当前自然语言审核 policy。
- `A`: operational action space，例如 `allow / contextualize / restrict / remove / escalate`。
- `M`: 一个或多个待测 LLM moderator。
- `D_optional`: 少量历史 case、stale guidance、current guidance 或 domain glossary。它们不是必需输入。
- `B`: 预算，例如最多生成多少 boundary family、多少 probe、多少模型调用。

### 输出

方法输出不是训练集，而是一个 specification gap report：

- `spec_graph`: 从 policy 解析出的 clause、risk、exception、action 映射。
- `candidate_boundary_variables`: 候选边界变量，如 `endorsement`、`debunking intent`、`official-looking format`。
- `probe_sets`: 每个 boundary family 下的 matched probes。
- `gap_scores`: 每个 family 的 instability、family error、action error、clarification gain。
- `gap_type`: `boundary insufficiency`、`action-granularity insufficiency`、`instruction-following failure`、`taxonomy ambiguity` 等。
- `minimal_clarification_candidates`: 最小 policy patch 或 action rubric 建议。
- `evidence_trace`: 每个结论对应的 probe、模型输出、rationale、before/after 变化。

## 方法总览

AutoBAP 是一个闭环：

```text
policy text
  -> policy decompiler
  -> boundary/action variable miner
  -> contrastive probe generator
  -> probe verifier and active selector
  -> multi-view model evaluator
  -> gap localizer
  -> minimal clarification synthesizer
  -> rescue validation
  -> gap report
```

核心研究味道在于：它把 policy sufficiency 变成一个可测试、可优化、可复核的问题，而不是停留在“policy 写得不清楚”的常识。

## 形式化目标

给定自然语言 policy `P`，AutoBAP 不直接学习一个新的 moderation classifier，而是测试 `P` 是否足以约束一个 operational decision function：

```text
f_P(x) -> y, where y in A
```

其中 `A` 是部署动作本体，例如：

```text
allow / contextualize / restrict / remove / escalate
```

一个 policy region 可以表示为：

```text
r = topic + boundary variable assignments
```

例如：

```text
election_misinformation_quote
  + stance = debunking
  + official_source = present
  + mobilization = none
```

如果从 policy text 无法为 `r` 推出稳定、唯一、可复核的 action，或者同一 region 在 paraphrase、模型、policy view 之间产生高波动，就说明该 region 存在 specification risk。

因此 AutoBAP 的方法目标不是提高平均 accuracy，而是估计：

```text
which policy regions are insufficiently specified,
which missing variable or action threshold causes the instability,
and whether a minimal clarification can repair it.
```

## 模块 1：Policy Decompiler

目标：把自然语言 policy 转成一个可测试的 specification graph。

输入：`P`、`A`。

输出：

```json
{
  "actions": ["allow", "contextualize", "restrict", "remove", "escalate"],
  "clauses": [
    {
      "clause_id": "civic_integrity_false_instruction",
      "risk": "false voting instruction",
      "trigger_conditions": ["current election", "actionable instruction", "false procedural claim"],
      "exceptions": ["future reform discussion", "educational correction"],
      "suggested_actions": ["remove", "contextualize"]
    }
  ],
  "underspecified_terms": [
    "educational correction",
    "official-looking",
    "borderline civic-integrity content"
  ]
}
```

自动化方式：

- 用 LLM 抽取 policy clause、action、exception、risk condition。
- 用 schema verifier 检查每个 action 是否在 `A` 中，每个 clause 是否能映射到至少一个 action。
- 对 vague terms、exception overlaps、多个 action 共享同一 condition 的位置打上 `underspecification candidate`。
- 每个 clause 必须保留 `evidence_span`，即它来自 policy 原文的哪一段；没有原文支撑的抽取项只能标为 hypothesis，不能当作 policy truth。

更严格地说，Policy Decompiler 输出的是一个 policy-to-operation IR：

```json
{
  "clause_id": "civic_false_instruction_remove",
  "evidence_span": "Remove content that gives false instructions about when, where, or how to vote.",
  "risk_target": "false voting instruction",
  "conditions": ["current election", "false procedural claim", "actionable instruction"],
  "exceptions": ["future reform discussion", "educational correction"],
  "surface_action": "remove",
  "canonical_action": "remove",
  "action_confidence": "explicit"
}
```

Action extraction 分两层：

1. `surface action extraction`
   - 从 policy 里抽取原始动作词，例如 `remove`、`label`、`downrank`、`review`、`permit`。

2. `canonical action mapping`
   - 映射到部署动作本体，例如：

| Surface phrase | Canonical action |
|---|---|
| no action, permit | `allow` |
| add notice, label, add context | `contextualize` |
| reduce distribution, limit reach | `restrict` |
| delete, take down, remove | `remove` |
| human review, legal review, high-risk queue | `escalate` |

如果 policy 只说 `take action`、`address appropriately`、`handle carefully`，系统不能强行映射成明确动作，而应标记为 `action underspecification`。

关键点：LLM 在这里是 parser/proposer，不是 policy owner。它只能提出候选结构，不能宣布真实边界。

## 模块 2：Boundary/Action Variable Miner

目标：自动找出最可能导致 policy-to-operation gap 的变量。

候选变量来源：

1. **exception boundary**
   - 例如：education/critique vs endorsement/mobilization。

2. **action adjacency**
   - 例如：`allow` vs `contextualize`，`remove` vs `escalate`。
   - 如果两个动作的条件高度重叠，就说明 action-granularity 可能不足。

3. **vague term expansion**
   - 例如：`official-looking` 可以拆成：
     - 是否使用政府 logo；
     - 是否要求用户立即行动；
     - 是否有 satire marker；
     - 是否现实可置信。

4. **policy conflict**
   - 同一内容同时触发 “educational exception” 和 “misinformation removal”。

5. **historical/stale guidance tension**
   - 历史 case 合理，但当前 policy 可能已经改变。

每个变量记录为：

```json
{
  "variable_id": "debunking_vs_endorsement",
  "family": "election_misinformation_quote",
  "source_clause_ids": ["civic_integrity_false_instruction", "education_exception"],
  "low_value": "quotes false claim to debunk it",
  "high_value": "quotes false claim to endorse it",
  "expected_action_contrast": ["contextualize", "remove"],
  "gap_hypothesis": "policy may not specify when quotation becomes amplification"
}
```

## 模块 3：Specification Region Graph

目标：把 policy clause、boundary variable 和 action edge 组合成一个可搜索的图。

定义图：

```text
G = (R, E)
```

- `R`: policy regions，即 topic + boundary/action variable assignments。
- `E`: matched contrastive edges，每条边只改变一个变量。
- 节点标签：`resolved`、`underspecified`、`contradictory`、`out_of_scope`。
- 边标签：`action_preserving`、`action_changing`、`unknown`。

潜在 gap 来自四类图结构：

1. `missing edge`
   - 变量改变了，但 policy 没说动作是否应该变化。

2. `multi-action region`
   - 同一 region 能被多个 action clause 支持。

3. `no-action region`
   - region 明显属于 policy scope，但没有 action rule。

4. `instability region`
   - policy-only 执行时，在 paraphrase、模型或采样之间出现 action 振荡。

这一步把“哪里可能不清楚”从主观直觉变成可枚举、可排序的 region-level 候选。

## 模块 4：Contrastive Probe Generator

目标：围绕每个候选变量生成 matched probes。

不是普通 synthetic data generation。普通合成数据追求覆盖和训练可用性；这里追求诊断性：

- 同一个 family 内 probes 表面尽量相似；
- 每次只改变一个 boundary variable；
- 每个 probe 都有明确的 expected decision family 和 expected action；
- 每组 probes 能回答“这个变量是否应该改变动作”。

关键原则是：

> **state-first, text-second**

也就是说，先生成结构化 case state，再把 state 渲染成自然语言内容。不能直接让 LLM 写一堆案例，因为这样很难保证 matched pair 真的只改变了一个变量。

结构化 state 示例：

```json
{
  "probe_type": "action",
  "target_variable": "official_debunking_source",
  "target_edge": "allow_contextualize",
  "invariants": {
    "domain": "election_moderation",
    "speaker_role": "ordinary_user",
    "claim_type": "false_ballot_claim",
    "stance": "debunking",
    "mobilization": "none"
  },
  "case_a": {
    "official_debunking_source": false,
    "expected_action": "allow"
  },
  "case_b": {
    "official_debunking_source": true,
    "expected_action": "contextualize"
  },
  "label_status": "gold|diagnostic|needs_policy_owner"
}
```

`label_status` 很重要：如果 policy 本身没有规定 official source 是否应把 `allow` 推到 `contextualize`，系统不能硬造 gold label，而应把该 pair 标成 `diagnostic` 或 `needs_policy_owner`。这样才能避免“模型自己生成、自己标注、自己证明”的循环。

示例：

```json
{
  "probe_id": "auto_election_quote_002",
  "family": "election_misinformation_quote",
  "varied_variable": "stance_toward_false_claim",
  "content": "A library post quotes a false ballot-validity rumor, marks it false, and links official election guidance.",
  "expected_decision_family": "intervention_without_removal",
  "expected_action": "contextualize",
  "matched_controls": ["auto_election_quote_001", "auto_election_quote_003"]
}
```

生成策略：

1. 先生成一个 base scenario。
2. 再生成最小编辑版本：
   - `debunking` -> `endorsement`
   - `satire marker present` -> `satire marker absent`
   - `general prediction` -> `false certification`
3. 约束 generator 必须输出 `diff_explanation`，说明两条 probe 只改变了哪个变量。

## 模块 5：Probe Verifier and Active Selector

LLM 生成的 probe 会有幻觉和低质量问题，所以必须有 verifier。

Verifier 检查：

- `single_variable_change`: 是否真的只改一个变量。
- `slot_diff`: 结构化 state 是否只改目标 slot。
- `text_reconstruction`: 从最终文本反抽变量后，是否仍然只改目标变量。
- `surface_match`: 主题、长度、风险语境是否相近。
- `policy_relevance`: 是否确实触发 policy clause。
- `action_validity`: expected action 是否属于 `A`。
- `answer_leakage`: content 是否直接泄露“应该 contextualize/remove”。
- `safety_filter`: 是否生成不必要的有害细节。

Active selector 选择最有信息量的 probes，而不是全跑：

```text
probe_score =
  model_disagreement
  + action_entropy
  + boundary_sensitivity
  + policy_clause_overlap
  + expected_clarification_gain
  - generation_quality_penalty
```

直觉：

- 多模型不一致，说明边界可能不充分。
- 相邻 action 间摇摆，说明 action-granularity 可能不充分。
- minimal edit 导致不成比例 action shift，说明边界可能被模型误解。
- clarification 后可能大幅下降的 probe 最值得优先测试。

## 模块 6：Multi-View Policy Evaluator

对每个 probe，运行多个 policy view：

1. `abstract_policy`
   - 原始 policy。

2. `boundary_clarified_policy`
   - 加入由 AutoBAP 生成或从 policy owner 获取的最小边界 clarification。

3. `boundary_plus_action_rubric`
   - 在边界 clarification 基础上加入 action 阈值。

4. 可选：`stale_or_data_first_guidance`
   - 模拟 BARRED-like / historical case / synthetic examples 先行时是否产生 pseudo-consensus 或 stale harm。

输出统一映射到：

```json
{
  "model": "qwen2.5:7b",
  "policy_view": "boundary_plus_action_rubric",
  "probe_id": "auto_election_quote_002",
  "decision": "contextualize",
  "decision_family": "intervention_without_removal",
  "rationale": "...",
  "used_policy_clauses": ["education_exception", "civic_integrity_false_instruction"],
  "used_precedents": []
}
```

## 模块 7：Gap Localizer

Gap localizer 把错误归因到不同机制。

核心规则：

```text
如果 abstract_policy 高 family error / 高 instability，
并且 boundary clarification 明显降低 family error：
  -> boundary insufficiency

如果 boundary clarification 降低 family error，
但 exact action error 仍高，
并且 action rubric 明显降低 exact action error：
  -> action-granularity insufficiency

如果 policy 已经明确，模型仍违反：
  -> instruction-following failure

如果多个模型高度一致，但 rationale 依赖 policy 没有授权的假设：
  -> pseudo-consensus candidate

如果 clarification 也不能降低错误：
  -> action taxonomy ambiguity / unresolved policy-owner judgment / model capability issue
```

这一步是论文方法的核心：我们不只报告模型错了，而是定位“错来自哪里”。

## 模块 8：Minimal Clarification Synthesizer

目标：自动提出最小 policy patch，并测试 patch 是否真的 rescue。

Patch 类型：

1. `boundary clarification`
   - 明确某个变量如何改变 decision family。

2. `action rubric`
   - 明确同一 family 内不同动作的阈值。

3. `positive/negative anchor`
   - 一正一反两个最小案例。

4. `stale invalidation`
   - 明确某类旧 precedent 不能迁移到当前 regime。

优化目标：

```text
maximize clarification_gain
minimize patch_length
minimize new_conflict
maximize coverage_on_holdout_probes
```

也就是不要写一大段万能规则，而是找最小能修复边界的 clarification。

## 模块 9：Rescue Validation

为了避免 patch 只是 overfit 当前 probes，需要做 holdout validation：

1. 每个 boundary family 生成 `train probes` 和 `holdout probes`。
2. minimal clarification 只根据 train probes 生成。
3. 在 holdout probes 上测试：
   - family error 是否下降；
   - exact action error 是否下降；
   - instability 是否下降；
   - 是否引入新 harm。

这能把方法从“调 prompt”提升到“specification repair generalizes over matched probes”。

## 算法伪代码

```text
AutoBAP(P, A, Models, Budget):
  S = DecompilePolicy(P, A)
  V = MineBoundaryAndActionVariables(S)
  G = BuildSpecificationRegionGraph(S, V)
  U = DetectUnderspecifiedRegions(G)
  C = []

  for region in U:
    candidates = GenerateStateFirstContrastiveProbes(P, S, G, region)
    verified = VerifyProbes(candidates, P, S, A)
    C.extend(verified)

  selected = ActiveSelect(C, Budget)
  train, holdout = SplitByFamilyAndEdge(selected)

  R_abstract = Evaluate(train, P, Models)
  gaps = LocalizeGaps(R_abstract, train, S, G)

  for gap in gaps:
    patch_boundary = SynthesizeBoundaryClarification(gap, S)
    R_boundary = Evaluate(train[gap.family], P + patch_boundary, Models)

    patch_action = SynthesizeActionRubric(gap, S, R_boundary)
    R_action = Evaluate(train[gap.family], P + patch_boundary + patch_action, Models)

    R_holdout = Evaluate(
      holdout[gap.family],
      P + patch_boundary + patch_action,
      Models
    )

    gap.update(MeasureRescue(R_abstract, R_boundary, R_action, R_holdout))

  return GapReport(S, G, selected, gaps)
```

## 多智能体实现方式

方法内部也可以自然使用 multi-agent，但不是为了“辩论出真值”，而是为了分离 proposer 和 verifier。

建议角色：

1. `Policy Parser Agent`
   - 只负责抽取 policy clause、action、exception。

2. `Boundary Miner Agent`
   - 只负责提出可能的 boundary variables。

3. `Probe Generator Agent`
   - 只负责生成 matched probes。

4. `Probe Verifier Agent`
   - 检查是否 single-variable change、是否 policy relevant、是否 action valid。

5. `Moderator Ensemble`
   - 多个模型/提示执行审核。

6. `Gap Localizer Agent`
   - 根据 before/after 指标归因 gap 类型。

7. `Patch Synthesizer Agent`
   - 提出 minimal clarification。

8. `Patch Critic Agent`
   - 检查 patch 是否引入过宽、过窄、与原 policy 冲突。

这个设计比 BARRED-like debate 更稳：debate 的目标通常是提高 synthetic labels 的一致性；这里的 multi-agent 目标是生成诊断证据并检查 specification 是否充分。

## 核心指标

### Probe quality

- `single_variable_validity`
- `surface_similarity`
- `policy_relevance_score`
- `answer_leakage_rate`

### Gap metrics

- `policy_only_decision_family_error_rate`
- `policy_only_exact_action_error_rate`
- `action_granularity_error_rate`
- `boundary_instability_rate`
- `model_disagreement_rate`
- `pseudo_consensus_candidate_rate`

### Clarification metrics

- `boundary_clarification_rescue_rate`
- `action_rubric_rescue_rate`
- `clarification_gain_per_token`
- `holdout_rescue_rate`
- `new_harm_rate`
- `differential_boundary_rescue`
- `differential_action_rescue`

其中两个 differential 指标是正式论文里最有机制味道的：

```text
differential_boundary_rescue =
  delta(decision_family_error) - delta(action_granularity_error)

differential_action_rescue =
  delta(action_granularity_error | family_correct)
```

直觉是：boundary clarification 应主要修 coarse family；action rubric 应主要修 family 已正确后的 exact action。如果两者没有差异，就说明我们的两层机制没有被实验支持。

### Distinguishing metrics

- `instruction_following_failure_rate`
- `taxonomy_ambiguity_rate`
- `unresolved_policy_owner_judgment_rate`
- `diagnostic_precision_recall_f1`

## 实验设计

### E0：diagnostic validity

这是把 pilot 变成方法论文的关键实验。

做法：

- 先让专家或研究者盲标一批 policy regions 的真实问题类型：
  - `boundary insufficiency`
  - `action-granularity insufficiency`
  - `both`
  - `instruction-following failure`
  - `not a policy gap`
  - `needs policy-owner judgment`
- AutoBAP 自动运行完整诊断。
- 比较系统输出的 gap type 与盲标结果，报告 region-level precision、recall、F1。

这证明系统不只是能让 error 下降，而是能正确说出“为什么错”。

### E1：自动 probe 质量

比较：

- 人工 probes；
- AutoBAP 自动 probes；
- 普通 LLM synthetic cases。

验证：

- 自动 probes 是否更像 matched contrastive tests；
- 是否更集中暴露 boundary/action instability；
- 是否比普通 synthetic cases 更省样本。

### E2：gap localization

运行四种 policy view，形成 2x2 对照：

- abstract；
- boundary-only；
- action-only；
- boundary + action rubric。

目标：

- boundary clarified 主要降低 decision-family error；
- action rubric 进一步降低 exact-action error；
- `action-only` 不应大幅修复 boundary error，否则说明 action rubric 携带了隐式 boundary 信息；
- `boundary-only` 不应完全修复 exact-action error，否则 action-granularity 独立性不成立；
- 复现当前 12-case pilot 的机制，但数据由自动方法生成。

### E3：active selection

比较：

- 随机 probes；
- 覆盖式 probes；
- AutoBAP active selected probes。

目标：

- 用更少 probes 找到更多 high-gap family；
- 更高 clarification gain per probe。

### E4：minimal clarification generalization

用 train probes 生成 clarification，在 holdout probes 上测试。

目标：

- 证明 patch 不是只修当前 case；
- 证明 action rubric 对同一 family 内新 case 也有帮助。

### E5：和 data-first / BARRED-like 区分

比较：

- synthetic examples 直接作为 few-shot / memory guidance；
- AutoBAP 先做 sufficiency testing，再决定是否需要 clarification。

目标：

- 展示 data-first 可能产生 high agreement / low anchor；
- AutoBAP 输出的是 gap report 和 minimal clarification evidence，不是直接训练标签。

### E6：必须做的 ablation 和 negative controls

为了防止审稿人认为这只是“多写点 policy 就更好”，需要以下对照：

1. `matched probes` vs `random/generated unpaired probes`
   - 证明 matched contrastive design 是方法核心。

2. `generator-only` vs `generator + verifier`
   - 证明 verifier 能减少伪 matched pair、变量混杂和 label leakage。

3. `same-model judge` vs `cross-model judge`
   - 避免系统自己生成、自己评估、自己证明。

4. `irrelevant clarification`
   - 加入无关 clarification 不应显著 rescue 当前 family。

5. `stale/misaligned guidance`
   - 证明错误 guidance 可能造成 harm，而不是任何额外上下文都有效。

6. `clear-policy negative control`
   - 对本来写得很清楚的 policy，系统不应误报大量 gap。

7. `instruction-following control`
   - 给同一模型非常明确、低歧义规则；如果仍失败，应归因于 model/prompt failure，而不是 policy gap。

## 论文贡献可以怎么写

1. 提出 `policy-to-operation specification gap`，指出 LLM moderation 失败不只来自模型能力，也来自 policy 是否足够可执行。

2. 提出 `AutoBAP`，一个自动化 policy specification testing 方法，用 policy decompilation、boundary variable mining、matched probe generation 和 clarification rescue 来定位 gap。

3. 区分 `boundary insufficiency` 与 `action-granularity insufficiency`，并设计 before/after policy-view 评估证明二者是不同层次。

4. 提出 active boundary probing：用模型不一致、action entropy、boundary sensitivity 和 expected clarification gain 选择最有信息量的 probes。

5. 证明 minimal clarification 可以用少量 policy patch 修复一类边界，而不是依赖大规模合成训练数据。

## 不能过度 claim 的地方

- 不能说 AutoBAP 自动恢复真实 policy intent。
- 不能说 LLM 生成的 clarification 可以不经审核直接上线。
- 不能说所有内容审核都能通过 action rubric 解决。
- 不能说 BARRED、DynaGuard 或 instruction following 工作错误。
- 不能把自动 probe 的 expected label 当成无争议真值。

更稳的 claim 是：

> AutoBAP automatically identifies and tests underspecified regions of a moderation policy, and produces evidence-backed minimal clarification candidates that reduce operational instability under controlled evaluation.

中文：

> AutoBAP 自动发现并测试审核政策中可能未充分规定的区域，并输出有证据支持的最小澄清建议；在受控实验中，这些澄清可以降低 operational decision 的不稳定性。

## 为什么这个方向比纯 pilot 更像方法

当前 12-case pilot 做的是：

```text
人工设计 probes -> 测 abstract/boundary/action policy -> 观察错误下降
```

AutoBAP 做的是：

```text
自动解析 policy
  -> 自动发现候选 gap
  -> 自动生成 matched probes
  -> 自动选择高价值 probes
  -> 自动定位 gap 类型
  -> 自动提出最小 clarification
  -> 自动在 holdout probes 上验证 rescue
```

这就从“现象发现”推进成了“诊断系统”。

## 下一步最小实现

建议先实现一个不太大的 `AutoBAP v0`：

1. 固定 election moderation policy。
2. 实现 policy-to-operation IR schema，保留 `evidence_span`、surface action、canonical action、action confidence。
3. 自动抽取 6 个 boundary/action variables，并构建 specification region graph。
4. 每个 variable 生成 4 条 state-first matched probes，共 24 条候选。
5. verifier 筛到 12-16 条高质量 probes，并标注 `gold / diagnostic / needs_policy_owner`。
6. 跑 2-3 个模型、4 个 policy view：`abstract`、`boundary-only`、`action-only`、`boundary+action`。
7. 用 train probes 生成 minimal clarification，在 holdout probes 上验证 rescue。
8. 自动输出 gap report，包括 gap type、differential rescue、clarification gain、new harm。
9. 手工抽查 5-8 个 high-gap probes，确认诊断是否合理。

如果 v0 成立，再扩到第二个 domain，例如 health misinformation 或 finance advice。

## 当前判断

这个自动方法值得推进。它保留了我们已经验证到的最强机制：

```text
boundary clarification -> lowers decision-family error
action rubric -> further lowers exact-action error
```

同时把方法复杂度从“手工 probe pilot”升级为：

```text
policy decompilation + active contrastive probing + gap localization + minimal clarification rescue
```

这会更像一篇可投论文的方法部分，也更能回应“这不就是写清楚规则吗”的质疑：我们不是直接写规则，而是自动测试自然语言 policy 在哪里还不足以成为可执行 specification。
