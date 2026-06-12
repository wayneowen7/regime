# Operational Memory v2 实验备忘

日期：2026-06-02

## 背景判断

当前 transparent setting 明确把 `regime_id`、`validity_scope`、`compatible_regimes` 暴露给模型。qwen2.5:7b 在这个设置下表现过稳，不应被解读为“regime-aware memory 方向没有意义”，而应被解读为：当前 prompt 已经把关键判别信息 oracle 化了。

在真实 operational memory 中，模型通常不会在每条历史 case 旁边看到“这条 precedent 对哪些 regime 有效、对当前 regime 是否 compatible”这类结构化标签。它看到的更接近历史帖文、历史决策和自然语言理由。transparent setting 把本应由检索层或记忆治理层处理的 validity 判断直接交给了生成模型，因此较强或较稳的模型可以主动避开 invalid precedent。这会压低 cross-regime contamination 信号，也会让 naive memory 看起来比真实部署场景更安全。

所以 qwen2.5:7b 的结果不是负结果，而是一个诊断信号：如果把 compatibility metadata 放进 prompt，实验测到的是“模型能否读懂显式标签并遵守标签”，而不是“长期记忆在缺少显式 regime metadata 时是否会把旧 rationale 带入新 regime”。论文主问题应回到 operational memory setting：自然 precedent 有效，但 regime validity 不显式暴露。

## Operational Memory v2 实验假设

Operational Memory v2 要把 memory view 从 transparent 改为 operational：

- naive memory prompt 只给历史 case 的 post、decision、rationale。
- 不给 `regime_id`、`validity_scope`、`compatible_regimes`。
- regime-aware 条件仍然在检索前做 regime 过滤，但 prompt 中也只呈现自然 precedent。
- transparent setting 保留为 diagnostic，用于确认当 metadata oracle 存在时，模型是否能够使用显式 validity 信号。

核心假设：

1. 同一 regime 的自然 precedent 仍应提升或稳定模型表现，尤其是 exact adherence。
2. naive memory 在缺少 compatibility metadata 时，更容易把跨 regime 的旧 precedent 或旧 rationale 用到当前 case。
3. regime-aware retrieval 即使不在 prompt 中暴露 metadata，也应通过检索前过滤降低 invalid precedent use 和 stale rationale。
4. stronger model 在 transparent setting 下的稳定性不应抹掉 operational setting 中的污染风险；如果 operational view 下 qwen2.5:7b 也出现差异，方向更值得扩大。

## 远端 4090 运行建议

远端目录沿用：

```bash
cd /home/lenovo/code/regime_moderation_pilot
```

建议先确保 v2 runner 支持 `memory_view=operational`。目标运行矩阵：

- 模型：`qwen2.5:7b`、`llama3.2:latest`
- cases：10
- conditions：`policy_only,naive_memory,regime_filtered,regime_aware`
- memory view：`operational`
- top-k：3

建议命令：

```bash
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m regime_pilot.run_llm_pilot \
  --model qwen2.5:7b \
  --conditions policy_only,naive_memory,regime_filtered,regime_aware \
  --top-k 3 \
  --limit-cases 10 \
  --memory-view operational \
  --output pilot/results/llm_qwen25_7b_10cases_4conds_operational.json
```

```bash
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m regime_pilot.run_llm_pilot \
  --model llama3.2:latest \
  --conditions policy_only,naive_memory,regime_filtered,regime_aware \
  --top-k 3 \
  --limit-cases 10 \
  --memory-view operational \
  --output pilot/results/llm_llama32_10cases_4conds_operational.json
```

对照 diagnostic 可保留 transparent view，但不要把它作为主结论：

```bash
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m regime_pilot.run_llm_pilot \
  --model qwen2.5:7b \
  --conditions policy_only,naive_memory,regime_filtered,regime_aware \
  --top-k 3 \
  --limit-cases 10 \
  --memory-view transparent \
  --output pilot/results/llm_qwen25_7b_10cases_4conds_transparent_diagnostic.json
```

如果当前代码尚未实现 `--memory-view`，下一步应先只改 prompt/rendering 层：检索和 evaluation schema 可以尽量复用，避免把 v2 变成大范围重写。

## 主要观察指标

优先看四类指标：

1. `decision_family_adherence`
   - 解释粗粒度方向是否正确，例如 allow/contextualize 与 restrict/remove 的大类是否对。
   - 这是判断模型是否总体理解政策方向的主指标。

2. exact adherence
   - 当前结果中的 `policy_adherence_rate` 可视为 exact adherence。
   - 用于观察 memory 是否改善细粒度 decision label，尤其是同一 regime precedent 的 utility。

3. `invalid_used_precedents`
   - 观察模型显式引用或使用了多少对当前 regime 无效的 precedent。
   - 在 operational view 中，它是 naive memory 是否产生 cross-regime contamination 的直接证据。

4. stale rationale
   - 未来补充。
   - 需要识别模型没有显式列出 invalid precedent id、但 rationale 仍继承了旧 regime 的理由结构或规范前提的情况。
   - 这可能比 `used_precedents` 更接近真实长期记忆污染。

## Go/Kill 标准

Go：

- qwen2.5:7b 或 llama3.2 至少一个模型在 operational view 下出现 naive memory 的 invalid precedent use 或 stale rationale。
- regime-aware / regime_filtered 相比 naive memory 明显降低 invalid precedent use。
- 同时 naive memory 或 regime-aware 对 same-regime case 有可见 utility，例如 exact adherence 高于 policy_only，或 rationale 更贴近目标 decision family。
- transparent diagnostic 与 operational view 形成可解释差异：transparent 稳，operational 暴露污染或细粒度偏移。

Kill 或降级为附录：

- operational view 下两个模型都没有 invalid precedent use、没有 stale rationale，也没有可解释的 exact adherence 差异。
- memory 条件相比 policy_only 没有稳定 utility，只产生随机波动。
- regime-aware filtering 不能降低 naive memory 的污染，或污染主要来自 prompt parsing / JSON 格式错误而不是 memory validity。
- 10 cases 结果无法形成方向性信号，且扩大到 60 cases 的成本不能带来更清晰的判别力。

中间态：

- 如果 llama3.2 有污染、qwen2.5:7b 没有污染：保留方向，但把 claim 写成 model-capability-dependent risk，并扩大 case set 或削弱 policy verbosity。
- 如果 qwen2.5:7b 在 operational view 下也出现污染：优先 Go，下一步扩到 60 cases，并加入 stale rationale 标注。
