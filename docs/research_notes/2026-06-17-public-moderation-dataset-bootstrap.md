# 公开内容审核数据集 bootstrap 记录

## 目的

Reddit BAO 的 removed/label=1 评论正文恢复严重受限，因此不再把 Reddit BAO 当作唯一主 benchmark。当前目标是快速验证：是否存在可下载、带正文、可映射到 policy-to-operation gap 的公开数据集，支撑后续方法实验。

本轮 bootstrap 每个数据集最多抽样 500 条。原始样本写入 `data/raw/dataset_bootstrap/`，不进入 git；只将 text-free 字段画像和可行性摘要写入 `pilot/results/dataset_bootstrap/`。

## 已尝试数据集

### Aegis 2.0

- 数据源：`nvidia/Aegis-AI-Content-Safety-Dataset-2.0`
- 状态：成功
- 抽样：500 条，来自 `train`
- 关键字段：
  - text: `prompt`, `response`
  - label: `prompt_label`, `response_label`, `violated_categories`
- 样本分布：
  - `prompt_label`: safe 246, unsafe 254
  - `response_label`: null 284, safe 148, unsafe 68
- 适配判断：
  - 适合作为内容审核主数据源。
  - 适合从 `violated_categories` 构造 abstract policy/taxonomy。
  - 原生没有明确 policy 文本和 action rubric，需要我们把 taxonomy 编译成 policy views。

### DynaBench / DynaGuard

- 数据源：`tomg-group-umd/DynaBench`
- 状态：成功
- 抽样：500 条，来自 `DynaBench:test`
- 关键字段：
  - policy: `policy`
  - text: `transcript`
  - label: `label`
- 样本分布：
  - `label`: PASS 255, FAIL 245
- 适配判断：
  - 非常适合做 policy-conditioned 对照。
  - 因为它本身和 DynaGuard 强相关，不应作为唯一主数据，否则创新性会被压缩。
  - 可以用于验证：当已有明确 policy 时，我们的 boundary/action clarification 是否仍能减少执行不稳定。

### BARRED

- 数据源：`Plurai/BARRED`
- 状态：成功
- 抽样：500 条，来自 4 个 predicate/config：
  - `message_repetition`: 158
  - `gps_disclosure`: 112
  - `healthe`: 200
  - `plan_verification`: 30
- 关键字段：
  - text: `transcript`, `task_input`, `original_task_output`, `violating_task_output`
  - policy: `rule`
  - label: `predicate_label`, `violation_type`
- 样本分布：
  - `predicate_label`: 0 为 239，1 为 231
- 适配判断：
  - 适合作为 BARRED-like 对照和 related-work anchoring。
  - 它本身就在弥补 policy-to-operation gap，不能成为我们唯一主实验。
  - 但它很适合用来评估：我们的 policy clarification 是否比 data-first synthetic probing 更容易解释、更少依赖大规模合成。

### WildGuardMix

- 数据源：`allenai/wildguardmix`
- 状态：失败
- 原因：HuggingFace gated dataset，需要认证。
- 适配判断：
  - 理论上很适合，因为它覆盖 prompt harmfulness、response harmfulness、refusal 等更接近 action granularity 的字段。
  - 当前不应阻塞主线；后续如果拿到 HF access token 或完成访问申请，再纳入。

## 当前结论

我们已经有足够数据启动下一阶段，不需要继续卡 Reddit：

1. 主实验优先用 Aegis 2.0，因为它是标准内容安全审核数据，类别覆盖较广，正文可用。
2. DynaBench 用作 policy-conditioned 强相关对照，验证在显式 policy 场景下的方法效果。
3. BARRED 用作 data-first/boundary probing 相关工作对照，避免审稿人说我们只是换壳 BARRED。
4. Reddit 降级为现实动机和真实社区规则来源：历史 removed cases 不可得，说明依赖历史违规样本恢复边界在真实审核场景中并不稳。

## 下一步建议

下一步不要直接跑大模型矩阵，而是先构造统一 benchmark schema：

```text
dataset_name
source_id
input_text
optional_response_text
abstract_policy
boundary_clarified_policy
action_rubric_policy
expected_decision_family
expected_action
category_or_rule
```

其中：

- Aegis 2.0 负责主 moderation taxonomy。
- DynaBench 负责原生 policy-conditioned case。
- BARRED 负责规则/谓词型边界 case。

第一版可以先各抽 100 条，构造 `abstract_policy -> boundary_clarified_policy -> action_rubric_policy` 三种 policy view，然后复用现有 LLM runner 跑 qwen/llama smoke。如果信号存在，再扩展到 500-1000 条。
