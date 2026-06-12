# POLAR-Compact v0 运行记录

## 目的

本轮把 POLAR-Compact 从概念推进到最小可运行版本：

```text
structured action-rubric policy
-> boundary/action IR
-> runner-friendly compact policy text
-> 远端 4090 小矩阵验证
```

本轮不声称已经自动恢复真实 policy，也不声称超过人工 action rubric。目标是验证：

1. POLAR-Compact 能接入现有 runner；
2. compact rendering 比 abstract policy 明显更好；
3. compact rendering 是否能在更短文本下接近人工 action rubric；
4. 哪些 boundary/action 信息不能被压缩掉。

## 新增代码与数据

新增代码：

- `pilot/src/regime_pilot/polar_compact.py`
- `tests/test_polar_compact.py`

新增数据产物：

- `pilot/data/polar_compact_policies_action_granularity.json`
- `pilot/data/polar_compact_sidecar_action_granularity.json`
- `pilot/data/polar_compact_contrast_sets_action_granularity.json`

新增脚本：

- `scripts/run_2026_06_12_polar_compact_experiments.ps1`

新增方案文档：

- `docs/research_notes/2026-06-12-polar-compact-technical-plan.md`

## 测试

本地：

```powershell
$env:PYTHONPATH='C:\Users\wayne\Documents\Codex\regime\pilot\src'
C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
```

结果：65 个 unittest 通过。

远端：

`scripts/run_2026_06_12_polar_compact_experiments.ps1` 在 `lenovo@10.147.18.151` 上同步代码后，也先跑了 unittest，结果 65 个通过。

## Prompt 长度

按 policy rule 文本长度统计：

| policy 文件 | 平均字符 | 最大字符 |
|---|---:|---:|
| `action_granularity_policies_abstract.json` | 121 | 146 |
| `action_granularity_policies_action_rubric.json` | 708 | 759 |
| `polar_compact_policies_action_granularity.json` | 695 | 746 |

第一次实现曾错误地把 standalone prompt wrapper 放进每个 runner rule，导致 POLAR-Compact 平均长度超过 1200 字符。已通过 TDD 增加约束，修正为 runner-friendly compact rule text。

## 远端小矩阵

模型：

- `qwen2.5:7b`
- `llama3.2:latest`

条件：

- `abstract`
- `action_rubric`
- `polar_compact`

运行设置：

- 12 条 action-granularity probes
- `policy_only,naive_memory,regime_aware`
- `memory_view=operational`
- `policy_view=full`
- `stale_warning=on`

## 结果

| policy 条件 | exact action error | decision-family error | action-granularity error | boundary instability |
|---|---:|---:|---:|---:|
| abstract | 0.6667 | 0.2500 | 0.4167 | 0.5833 |
| action_rubric | 0.3333 | 0.0417 | 0.2917 | 0.0833 |
| polar_compact | 0.4167 | 0.0417 | 0.3750 | 0.1667 |

对比：

| 对比 | exact delta | family delta | action-granularity delta | instability delta |
|---|---:|---:|---:|---:|
| abstract -> polar_compact | -0.2500 | -0.2083 | -0.0417 | -0.4167 |
| action_rubric -> polar_compact | +0.0833 | 0.0000 | +0.0833 | +0.0833 |

## 初步解释

POLAR-Compact v0 明显优于 abstract policy，说明 boundary/action operationalization 的方向仍然成立。

但 POLAR-Compact v0 略弱于人工 action_rubric，说明当前 deterministic compact rendering 不是最终方法。它保住了 decision-family error，但在 exact action 和 instability 上损失了一点。

关键退化 case：

- `AG-T-007`
- family: `obvious_satire_vs_deceptive_notice`
- expected: `remove`
- post: 官方样式 county seal + “OFFICIAL NOTICE: Precinct 8 voting is canceled today” + 很弱的 `lol parody` 标签
- action_rubric policy-only decisions: `allow, remove`
- polar_compact policy-only decisions: `allow, escalate`

这个 case 表明：官方样式、current cancellation、weak parody label、高混淆风险这些词是 boundary-critical phrases。compact compiler 不能只做格式压缩，需要识别并保留这些关键短语，避免模型在 `remove` 和 `escalate` 或 `allow` 之间摇摆。

## 下一步

下一步要从“格式化 compiler”推进到“probe-guided compiler”：

1. 增加 boundary-critical phrase preservation：
   - 从 contrast sets 中抽取能区分 action edge 的变量；
   - 对每个 action rubric 保留对应变量短语。
2. 加 `LLM rewrite` baseline：
   - 让 LLM 直接把 abstract policy 改写详细；
   - 比较它和 POLAR-Compact 的 exact-action/error/instability。
3. 加 length-matched baseline：
   - 与 POLAR-Compact 控制相近长度；
   - 排除“只是更长/更短”的解释。
4. 单独围绕 `satire/deceptive notice` 做 4-6 条 follow-up probes：
   - 检查 weak parody label、official-looking format、current cancellation、coordination 四个变量。

当前结论：

> POLAR-Compact v0 已经证明 compact operationalization 比 abstract policy 有效，但也暴露出核心方法问题：compiler 必须由 boundary-action contrast data 指导，而不能只是压缩或重排 action rubric。
