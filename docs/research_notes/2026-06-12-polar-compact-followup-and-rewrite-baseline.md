# 2026-06-12 POLAR-Compact follow-up 与 rewrite baseline 记录

## 这一轮要回答的问题

上一轮已经证明了一个基础现象：

- `boundary clarification` 主要降低 decision-family error；
- `action rubric` 进一步降低 exact-action error；
- 代表性案例 `AG-T-002` 展示了 `remove -> allow -> contextualize` 的转变。

这一轮推进的问题是：如果我们提出 **POLAR-Compact / boundary-action data guided policy operationalization compiler**，它到底是不是只等价于“把 prompt 写详细一点”？

因此本轮补了两类东西：

1. 在 POLAR-Compact 中加入由 contrast cases 提取的 `action-edge cues`。
2. 增加普通 rewrite baseline，比较“模板式改写”和“长度匹配改写”是否也能弥合 policy-to-operation gap。

## 新增产物

代码：

- `pilot/src/regime_pilot/rewrite_baselines.py`
- `tests/test_rewrite_baselines.py`
- `pilot/src/regime_pilot/polar_compact.py`：补充 action-bound cues 编译逻辑
- `tests/test_polar_compact.py`：补充 action-edge cues preservation 测试

脚本：

- `scripts/run_2026_06_12_polar_compact_experiments.ps1`
- `scripts/run_2026_06_12_rewrite_baseline_experiments.ps1`

数据/结果：

- `pilot/data/polar_compact_policies_action_granularity.json`
- `pilot/data/polar_compact_sidecar_action_granularity.json`
- `pilot/data/polar_compact_contrast_sets_action_granularity.json`
- `pilot/data/rewrite_template_policies_action_granularity.json`
- `pilot/data/rewrite_length_matched_policies_action_granularity.json`
- `pilot/results/remote_20260612_polar_compact_*`
- `pilot/results/remote_20260612_rewrite_baseline_*`

## 实验设置

模型：

- `qwen2.5:7b`
- `llama3.2:latest`

数据：

- 12 条 action-granularity probes
- 主要看 `policy_only`，同时保留 `naive_memory` / `regime_aware` 结果用于后续分析

政策条件：

| 条件 | 含义 |
|---|---|
| `abstract` | 高层抽象政策 |
| `rewrite_template` | 不看 cases 的模板式操作化改写 |
| `rewrite_length_matched` | 不看 cases 的长度匹配改写 |
| `action_rubric` | 人工 action rubric，上界参照 |
| `polar_compact` | 当前 deterministic compiler 输出，包含 action-edge cues |

## 主结果

| policy | exact action error | decision-family error | action-granularity error | boundary instability |
|---|---:|---:|---:|---:|
| abstract | 0.6667 | 0.2500 | 0.4167 | 0.5833 |
| rewrite_template | 0.6250 | 0.2500 | 0.3750 | 0.4167 |
| rewrite_length_matched | 0.6250 | 0.1667 | 0.4583 | 0.2500 |
| action_rubric | 0.3333 | 0.0417 | 0.2917 | 0.0833 |
| polar_compact | 0.3333 | 0.1667 | 0.1667 | 0.3333 |

解释：

1. 普通 rewrite baseline 只带来很弱的改善。`exact action error` 仍是 `0.6250`，远高于 `action_rubric` 和 `polar_compact` 的 `0.3333`。
2. length-matched rewrite 并没有解决动作粒度问题，`action-granularity error` 反而为 `0.4583`，比 abstract 的 `0.4167` 更差。
3. POLAR-Compact 追平了人工 action rubric 的 exact action error，并把 action-granularity error 降到 `0.1667`。
4. 但 POLAR-Compact 的 decision-family error 和 instability 明显弱于人工 action rubric，说明当前 compiler 还会把某些 boundary cue 权重放错。

这支持一个比较稳的论文表述：

> Policy-to-operation gap 不能靠普通 prompt rewrite 或单纯增加长度解决；需要 boundary-action contrast data 指导 policy operationalization。但当前 deterministic compiler 还不是最终方法，它暴露出 cue selection、cue weighting 和 conflict handling 是下一步核心技术问题。

## Prompt 长度

| policy | 平均 rule 字符数 | 最大 rule 字符数 |
|---|---:|---:|
| abstract | 123.0 | 148 |
| rewrite_template | 520.3 | 548 |
| rewrite_length_matched | 809.8 | 873 |
| action_rubric | 708.0 | 759 |
| polar_compact | 959.0 | 1258 |

重要限制：

- 当前 action-edge 版 POLAR-Compact 已经不够 compact，平均长度超过了人工 action rubric。
- 因此不能 claim “更短 prompt 达到同等效果”。
- 更合适的 claim 是：当前版本证明了 boundary-action cues 的结构信号有价值，但 v1 必须做 cue selection / compression，使 deployment policy 不只是堆叠 cues。

## 关键 case

### AG-T-002：主叙事案例

Expected：`contextualize`

| 条件 | qwen2.5:7b | llama3.2 |
|---|---|---|
| abstract | remove | remove |
| rewrite_template | remove | remove |
| rewrite_length_matched | remove | remove |
| action_rubric | contextualize | contextualize |
| polar_compact | contextualize | contextualize |

这说明普通 rewrite 没有学到“纠错性引用 + 官方来源 + heightened period”应该走 `contextualize`，而 boundary/action 结构化操作化可以修复这个动作边界。

### AG-T-004：mobilization escalation

Expected：`escalate`

| 条件 | qwen2.5:7b | llama3.2 |
|---|---|---|
| rewrite_template | remove | remove |
| rewrite_length_matched | remove | remove |
| action_rubric | escalate | escalate |
| polar_compact | escalate | escalate |

这说明普通 rewrite 即使更长，也容易把“有害但普通删除”和“目标群体 + 即时线下动员”的升级边界混在一起。

### AG-T-005 到 AG-T-008：satire edge 仍是失败集中区

POLAR-Compact 在 education/mobilization 组表现很好，但在 satire 组不稳定：

- `AG-T-005` expected `allow`，POLAR-Compact 中 `llama3.2` 判成 `remove`。
- `AG-T-006` expected `contextualize`，POLAR-Compact 中 `qwen2.5` 判成 `allow`，`llama3.2` 判成 `remove`。
- `AG-T-007` expected `remove`，POLAR-Compact 中 `qwen2.5` 仍判成 `allow`。
- `AG-T-008` expected `escalate`，POLAR-Compact 中 `qwen2.5` 判成 `remove`。

这说明 satire/deceptive notice 的变量不是简单列出来就够了。compiler 需要理解：

- official-looking format 是否真实指向当前投票安排；
- parody label 是否足够强；
- confusion risk 是否高到 intervention；
- coordination / multi-account 是否把 remove 推到 escalate。

换句话说，失败不是“再手写一点规则就行”，而是说明需要一个更正式的 `cue -> action edge` 权重和冲突解析机制。

## 与普通 prompt rewrite 的区别

本轮 rewrite baseline 很关键，因为它挡住了一个潜在审稿质疑：

> 你们是不是只是把 policy prompt 写得更详细？

当前结果的回答是：不是。

- template rewrite 从 `0.6667` 降到 `0.6250`，改善很小；
- length-matched rewrite 也停在 `0.6250`；
- POLAR-Compact 达到 `0.3333`，但它的优势不是来自“随便写长”，而是来自 action-edge cues 的结构化组织。

不过要谨慎：当前 POLAR-Compact 比 length-matched rewrite 更长，所以仍需补一个更严格的 v1：

- 同等长度或更短长度下比较；
- cue selection 不依赖手工补短语；
- sidecar 保留 cue 来源，但 deployment prompt 只保留最小必要 cues。

## 当前论文判断

这一轮结果让方向更稳了，但也更清楚地暴露了方法缺口。

可以推进的主问题：

> 高层 moderation policy 与真实执行需求之间存在 policy-to-operation gap。普通 prompt rewrite 和长度增加不足以稳定弥合这个 gap；需要用 boundary-action probes 诊断缺失的 action edge，并把这些诊断结果编译成可部署的 operational policy。

当前贡献雏形：

1. 提出 policy-to-operation gap 的 action-granularity 版本：不仅要判 allow/remove，还要判 contextualize/remove/escalate 等具体动作。
2. 构造 boundary-action contrast probes，用于定位哪些变量改变了 decision family，哪些变量只改变 exact action。
3. 提出 POLAR-Compact compiler 雏形：把 boundary/action IR 和 contrast-derived cues 编译成 deployment policy，同时把证据留在 sidecar。
4. 通过 rewrite baseline 证明：普通 prompt rewrite 或长度匹配并不能充分解决 gap。

不能过度 claim：

- 不能说当前 compiler 已经优于人工 action rubric。
- 不能说当前版本已经足够 compact。
- 不能说已经自动恢复真实 policy boundary。
- 不能把 action-edge cues 写成“人工补充更细规则后提升效果”。

## 下一步

最关键的下一步不是继续堆 case，而是把 compiler v1 变得更像方法：

1. **Cue selection**：从 contrast set 自动选择最小 action-edge cues，限制 prompt 长度。
2. **Cue weighting**：区分强 cue、弱 cue、必要 cue、禁止 cue，避免 satire 组的过度移除。
3. **Conflict handling**：当 `parody label` 和 `official-looking current notice` 同时存在时，显式决定谁优先。
4. **Length-controlled POLAR**：把 POLAR-Compact v1 控制到接近 action_rubric 或 rewrite_length_matched 的长度，再重跑对比。
5. **真 LLM rewrite baseline**：后续可以让强模型直接把 abstract policy 改写为 operational policy，作为更强的 prompt baseline。

短期验收标准：

- 在不增加平均长度的情况下，保持或降低 exact action error；
- 把 satire 组的 family error 从 `0.375` 拉回接近 action_rubric 的 `0.125`；
- 保持 `AG-T-002`、`AG-T-004` 的成功；
- 修复 `AG-T-005/006/007/008` 至少两个 case 的模型间不稳定。
