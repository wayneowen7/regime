# 2026-06-09 Policy-to-Operation Gap Artifacts

本文件记录 2026-06-09 围绕 policy-to-operation specification gap 新增的论文推进材料。

## Core Documents

### `docs/research_notes/2026-06-09-action-granularity-mechanism-run.md`

用途：

- 记录 2026-06-09 action-granularity 小型机制验证的完整运行结果。
- 报告 12 条 probes、3 个 policy 条件、2 个模型的结果。
- 固化关键结论：boundary clarification 主要降低 decision-family error；action rubric 进一步降低 exact-action/action-granularity error。

### `docs/research_notes/2026-06-09-policy-to-operation-gap-paper-direction.md`

用途：

- 固化当前最推荐论文方向：policy-to-operation specification gap。
- 明确 boundary sufficiency 与 action-granularity sufficiency 的关系。
- 记录与 Policy-as-Prompt、DynaGuard、BARRED、evolving policy QA、HateModerate、GuardBench、GuardSet-X、GSPR、TSPA 行业实践的边界。
- 给出最小下一步实验：boundary replication、action-granularity experiment、boundary/action 2x2 separation。

### `docs/research_notes/2026-06-09-policy-to-operation-gap-introduction-draft.md`

用途：

- 保存论文标题、abstract、introduction、contributions 初稿。
- 可作为后续重写 `iclr2025_conference.tex` introduction 的直接素材。

## Current Framing

一句话：

> 我们提出面向 LLM 内容审核的 policy specification testing methodology，用 boundary/action probes 发现 high-level policy 到 operational moderation decision 之间尚未被充分规定的边界变量和动作阈值。

## Next Priority

下一步最小实验应优先验证：

```text
boundary clarification -> lowers decision-family error
action rubric -> further lowers exact-action error
```

不要优先扩成大规模 benchmark。

## Reproduction Script

### `scripts/run_2026_06_09_action_granularity_experiments.ps1`

用途：

- 同步本地 `docs/pilot/tests/scripts` 到远端 4090。
- 运行远端 unittest。
- 串行运行 2 模型 x 3 policy 条件 x 12 cases 的 action-granularity 小矩阵。
- 生成 analysis 和 comparison JSON 并拉回本地。
