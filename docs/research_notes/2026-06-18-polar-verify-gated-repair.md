# 2026-06-18 POLAR-Verify：带验证门控的 policy repair 实验记录

## 核心结论

昨天的 POLAR-Active v2 证明了一个负面但重要的结论：**直接把错误 cue 追加回 policy，会过拟合局部 probe，并引入新的 action confusion**。今天推进的 POLAR-Verify 把方法改成：

```text
gap localization
-> atomic patch proposal
-> single-patch candidate policy
-> target rescue / no-harm verifier
-> accepted patch compiled policy
```

这一版结果是正向的：8 个自动生成 patch 中，verifier 只接受 1 个，拒绝 7 个；被接受的 patch 在 full12 两模型矩阵上比 POLAR-Compact 更好，同时避免了 naive v2 的退化。

## 方法变化

### 1. Patch 带 provenance

`IRPatch` 新增 `affected_case_ids`，每个 patch 都知道自己试图修复哪些 probes。这一点很关键，否则 verifier 无法判断 patch 是真的救了目标 case，还是只是碰巧改变了全局分数。

### 2. 每个 patch 单独编译 candidate policy

新增 artifact：

- `pilot/data/polar_verify_candidates_action_granularity_manifest.json`
- `pilot/data/polar_verify_candidates_action_granularity/patch_0001_policy.json`
- ...
- `pilot/data/polar_verify_candidates_action_granularity/patch_0008_policy.json`

每个 candidate policy 只包含一个 patch，因此可以做 patch-level attribution。

### 3. Verifier 接受规则

当前第一版 verifier 使用保守规则：

- target rescue：patch 对应的 affected case 至少被救回一个。
- exact no-harm：`policy_only_exact_action_error_rate` 不上升。
- family no-harm：`policy_only_decision_family_error_rate` 不上升。
- instability no-harm：`boundary_instability_rate` 不上升。
- non-target no-harm：非目标 case 不能从正确变成错误。

这不是最终最优规则，但它已经足以证明：自动 patch 不能直接全接收，需要验证门控。

## 实验设置

数据：

- 12 条 action-granularity probes。
- 8 个 atomic candidate patches，来自 POLAR-Active gap localization。

模型：

- `qwen2.5:7b`
- `llama3.2:latest`

远端：

- `lenovo@10.147.18.151`
- 每个 atomic patch 用 `policy_only` 跑 12 cases。
- accepted policy 再跑完整三条件矩阵：`policy_only,naive_memory,regime_aware`。

重要命令约束：

- 所有正式矩阵必须显式写 `--limit-cases 12`，否则 `run_llm_pilot.py` 默认只跑 3 条。

## Verifier 结果

8 个 patch 的接受结果：

| patch | target | decision | reason |
|---|---|---|---|
| patch-0001 | AG-T-010 | accepted | target rescue 1, no harm |
| patch-0002 | AG-T-005 | rejected | no rescue, non-target harm, exact error harm |
| patch-0003 | AG-T-006 | rejected | no rescue, exact error harm |
| patch-0004 | AG-T-007 | rejected | no rescue, exact/family/instability harm |
| patch-0005 | AG-T-010 | rejected | no rescue |
| patch-0006 | AG-T-012 | rejected | no rescue, non-target harm, exact/family/instability harm |
| patch-0007 | AG-T-006 | rejected | target rescue exists, but non-target harm and exact error harm |
| patch-0008 | AG-T-008 | rejected | no rescue, exact error harm |

这里 `patch-0007` 很有价值：它能救目标 case，但会伤害非目标 case，所以被拒绝。这正是 verifier 存在的意义。

## Full12 结果

| policy | exact action error | decision-family error | action-granularity error | instability |
|---|---:|---:|---:|---:|
| POLAR-Compact | 0.3333 | 0.1667 | 0.1667 | 0.3333 |
| naive POLAR-Active v2 | 0.4167 | 0.1250 | 0.2917 | 0.5000 |
| POLAR-Verify accepted | 0.2917 | 0.1250 | 0.1667 | 0.3333 |
| human action-rubric | 0.3333 | 0.0417 | 0.2917 | 0.0833 |

解释：

- 相比 POLAR-Compact，POLAR-Verify accepted 把 exact action error 从 `0.3333` 降到 `0.2917`。
- decision-family error 从 `0.1667` 降到 `0.1250`。
- action-granularity error 保持 `0.1667`，没有变差。
- instability 保持 `0.3333`，没有像 naive v2 那样升到 `0.5000`。
- 相比 naive POLAR-Active v2，verifier 明显阻止了错误 patch 的累积伤害。

注意：POLAR-Verify accepted 在 decision-family error 和 instability 上仍然不如 human action-rubric，说明 verifier 不是最终方法，只是把 naive repair 推进成了更可靠的自动闭环。

## Case 级观察

POLAR-Compact 的两个主要错误：

- `AG-T-006`: expected `contextualize`，模型在 `allow/remove` 之间摇摆。
- `AG-T-010`: expected `contextualize`，模型在 `allow/remove` 之间摇摆。

POLAR-Verify accepted 后：

- `AG-T-010` 被部分救回：policy-only decisions 变成 `contextualize/allow`，至少一个模型到达目标 action，row-level exact error 下降。
- `AG-T-006` 仍然失败，satire/deceptive notice family 仍是最大难点。
- `AG-T-008` 和 `AG-T-012` 的 escalation edge 没有被 naive patch 拉坏，保持和 POLAR-Compact 一样的行为。

这说明 verifier 的作用不是“万能修复”，而是避免坏 patch 把已经正确的 escalation edge 破坏掉。

## 论文意义

这轮结果让方法论更清晰了：

1. **不是 prompt rewrite**：我们不是把 policy 写长，而是做 patch-level specification repair。
2. **不是单纯合成数据**：candidate probes 用来诊断和验证 patch，不是直接拿去训练。
3. **不是人工规则堆叠**：每个 patch 都有 affected probe、candidate policy、target rescue、no-harm evidence。
4. **核心技术问题变成 patch acceptance**：哪些自动发现的 policy gaps 应该进入 deployment policy，哪些应该被拒绝。

更好的论文表述可以是：

> We study policy-to-operation gaps as a patch acceptance problem for moderation policies: automatically localized boundary/action gaps should not be blindly compiled into deployment policies; they must be validated by target rescue and no-harm constraints.

中文表达：

> 我们不是声称自动生成的每条规则都正确，而是提出一种可验证的 policy specification repair 框架：自动定位 gap，生成最小 patch，再通过 target rescue 和 no-harm gate 决定是否接受。

## 下一步

短期最关键的下一步不是继续堆模型，而是加强 verifier：

1. **Held-out neighboring probes**
   - 当前 no-harm 只看已有 12 条 probes。
   - 需要围绕被接受 patch 自动生成相邻 probes，验证是否过拟合。

2. **Patch combination search**
   - 当前只验证 single patch。
   - 后续要验证 accepted patch 之间是否组合后仍然 no-harm。

3. **Priority-rule patch**
   - satire family 失败说明 cue listing 不够。
   - 下一版应生成 priority patch，例如 `current official-looking disruption > weak parody label`。

4. **更强 baseline**
   - 加一个 strong LLM policy rewrite baseline，避免审稿人说 verifier 只是绕远路改 prompt。

5. **更大但仍可控的 probe set**
   - 先扩展 satire/deceptive notice family，因为这是当前最难、最能体现方法价值的部分。
