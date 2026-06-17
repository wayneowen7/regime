# 2026-06-17 POLAR-Active 方法实现与 ablation 记录

## 一句话结论

本轮实现了 POLAR-Active 的第一版自动闭环：从已有模型错误中定位 `boundary/action` specification gap，生成结构化 patch，再编译成可部署 policy。实验结果很重要但不完全正向：**gap localization 是有信号的，但 naive patch compiler 不能作为最终方法**。直接把失败 cue 追加回 policy 会修复部分 case，同时引入新的 action confusion 和模型间不稳定。

因此，论文方法应该从 `diagnose -> compile` 升级为：

```text
diagnose gaps -> propose atomic patches -> verify rescue/no-harm -> accept patches -> compile policy
```

也就是说，POLAR-Active 的核心不应只是“自动写更详细的 policy”，而应是 **policy specification repair with verifier**。

## 本轮实现内容

新增代码：

- `pilot/src/regime_pilot/polar_active.py`
  - 读取已有 LLM 结果和 probe metadata。
  - 将失败分类为 `missing_boundary` 或 `missing_action_edge`。
  - 按 `regime_id + rule_id + boundary_family + action_contrast` 定位 gap。
  - 生成结构化 `IRPatch`，只保留 cue/action-edge 信息，不写入 raw case text。
  - 编译成 policy JSON，并输出 sidecar/gap report/summary。

新增测试：

- `tests/test_polar_active.py`
  - 验证 metadata 解析。
  - 验证 boundary/action gap 分类。
  - 验证 patch IR 生成。
  - 验证 raw case text 不进入 policy。
  - 验证 patch 是 regime-specific，不会把一个 regime 的 gap 写到另一个 regime 的同名 rule。

新增实验 artifact：

- `pilot/data/polar_active_v2_policies_action_granularity.json`
- `pilot/data/polar_active_v2_sidecar_action_granularity.json`
- `pilot/results/polar_active_v2_action_granularity_gap_report.json`
- `pilot/results/polar_active_v2_action_granularity_summary.json`
- `pilot/data/polar_active_boundary_only_policies_action_granularity.json`
- `pilot/data/polar_active_boundary_only_sidecar_action_granularity.json`
- `pilot/results/polar_active_boundary_only_action_granularity_gap_report.json`
- `pilot/results/polar_active_boundary_only_action_granularity_summary.json`

## 一个重要工程坑

`run_llm_pilot.py` 的 CLI 默认 `--limit-cases=3`，如果不显式传 `--limit-cases 12`，文件名即使写了 `12case`，实际也只会跑前三条 case。本轮第一次远端运行就踩到了这个坑，后来已重跑 full12。

后续所有正式小矩阵都必须显式写：

```bash
--limit-cases 12
```

## POLAR-Active v2：完整自动 patch

v2 修复了两个实现问题：

1. patch 必须绑定到 `regime_id + rule_id`，不能只按 `rule_id` 全局应用。
2. patch 文本必须是短 action-edge 表述，不能把失败日志长句直接追加到 policy。

v2 artifact 统计：

| item | value |
|---|---:|
| detected gaps | 8 |
| generated patches | 8 |
| applied patches | 8 |
| dropped patches | 0 |
| patched rules | 2 |
| max rule chars | 3051 |

v2 远端 full12 结果，模型为 `qwen2.5:7b` 和 `llama3.2:latest`：

| policy | exact action error | decision-family error | action-granularity error | instability |
|---|---:|---:|---:|---:|
| POLAR-Compact baseline | 0.3333 | 0.1667 | 0.1667 | 0.3333 |
| POLAR-Active v2 | 0.4167 | 0.1250 | 0.2917 | 0.5000 |

解释：

- v2 降低了 decision-family error：`0.1667 -> 0.1250`。
- 但 exact action error 变差：`0.3333 -> 0.4167`。
- action-granularity error 变差：`0.1667 -> 0.2917`。
- 模型间不稳定性变差：`0.3333 -> 0.5000`。

这说明 v2 的 gap localization 找到了真实边界信号，但 patch compiler 过于贪心，直接追加多个 cue/action-edge 会让模型在相邻动作之间更摇摆。

## Boundary-only ablation

为了判断问题是否来自 action-edge patch，本轮又跑了只应用 `missing_boundary` patch 的 ablation。

boundary-only artifact 统计：

| item | value |
|---|---:|
| generated patches | 4 |
| applied patches | 4 |
| dropped patches | 0 |
| patched rules | 2 |
| max rule chars | 2349 |

结果：

| policy | exact action error | decision-family error | action-granularity error | instability |
|---|---:|---:|---:|---:|
| POLAR-Compact baseline | 0.3333 | 0.1667 | 0.1667 | 0.3333 |
| boundary-only | 0.4167 | 0.1667 | 0.2500 | 0.4167 |

解释：

- boundary-only 没有超过 POLAR-Compact。
- 它比 full v2 在 satire family 上稍微稳定，但总体仍然变差。
- 因此问题不是某一个 action-edge patch 的单点错误，而是 naive patch acceptance 缺少 verifier/no-harm 机制。

## Case 级观察

POLAR-Compact 的主要错误集中在：

- `AG-T-006`: expected `contextualize`，模型在 `allow/remove` 之间摇摆。
- `AG-T-010`: expected `contextualize`，模型在 `allow/remove` 之间摇摆。

POLAR-Active v2 的错误变成：

- `AG-T-006`: 仍然没有修复，仍在 `allow/remove` 之间摇摆。
- `AG-T-008`: expected `escalate`，v2 退化为 `remove`。
- `AG-T-012`: expected `escalate`，v2 退化为 `remove`。

这说明 v2 确实改变了模型行为，但它没有可靠地把行为推向目标 action；尤其是 escalation edge 很容易被压回普通 `remove`。

## 方法层面的判断

当前结果不应被写成“POLAR-Active 已经提升效果”。更准确的论文判断是：

1. **问题成立**：抽象 policy 到 operational action 之间确实存在 gap，尤其体现在 `contextualize/remove/escalate` 等 action granularity 上。
2. **定位有信号**：错误可以被解释为 missing boundary 或 missing action edge，而不是纯粹随机模型错误。
3. **naive repair 被证伪**：直接把失败 cue 追加成 policy patch 会过拟合局部 probe，并产生新的不稳定。
4. **下一版方法必须引入 verifier**：每个 atomic patch 应该先经过 local rescue、held-out no-harm、cross-model stability 检查，再被接受进入 compiled policy。

这反而使研究问题更像顶会论文：我们不是简单提出“更详细 prompt”，而是在研究 **policy specification repair 的 patch acceptance 问题**。

## 下一步方法设计

建议把方法升级为 `POLAR-Verify`：

1. **Atomic patch generation**
   - 每个 gap 生成一个最小 patch。
   - patch 只声明一个 action edge 或一个 priority rule。

2. **Patch-level validation**
   - 对每个 patch 单独编译候选 policy。
   - 在 target probes 上检查是否 rescue。
   - 在 neighboring probes 上检查是否 harm。

3. **Acceptance rule**
   - 接受条件示例：
     - target rescue 至少 1 个模型生效；
     - exact-action error 不上升；
     - decision-family error 不上升；
     - instability 不上升；
     - prompt length 在预算内。

4. **Conflict resolution**
   - 对 satire/deceptive notice 这类 family，不能只列 cue。
   - 必须显式表达 priority，例如：`current official-looking disruption > weak parody label`。

5. **Held-out check**
   - 不能只在生成 patch 的 probe 上验证。
   - 需要相邻 matched probes 或新生成 probes 做 no-harm。

## 论文写法上的启发

当前最稳的 contribution 不是“我们已经自动生成最优 policy”，而是：

- 提出 policy-to-operation gap 的 action-granularity 版本。
- 提出 boundary/action probe 用于诊断 specification insufficiency。
- 证明普通 rewrite 和 naive patch 都不足以稳定解决 gap。
- 提出带 verifier 的 policy specification repair 框架。

这会比“我们用 LLM 自动改 prompt 提升分数”更有学术味道，也更能避开 prompt engineering 的质疑。
