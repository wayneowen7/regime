# 4090 远端运行记录

日期：2026-06-02

## 远端环境

服务器：

`lenovo@10.147.18.151`

远端工作目录：

`/home/lenovo/code/regime_moderation_pilot`

GPU：

- NVIDIA GeForce RTX 4090
- 显存 24GB
- 驱动 535.183.01
- CUDA 12.2

Python 环境：

`/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python`

环境确认：

- Python 3.10.14
- torch 2.5.1+cu124
- CUDA available: true

Ollama 本地模型：

- `qwen3.6:27b`
- `qwen3:14b`
- `qwen2.5:14b`
- `qwen2.5:7b`
- `llama3.2:latest`
- `mistral-small3.1:latest`
- `gemma3:27b`
- 以及若干其他模型

## 上传与远端验证

上传方式：

1. 本地打包 `docs/`、`pilot/`、`tests/`。
2. 用 `scp` 上传到远端。
3. 在远端解包到 `/home/lenovo/code/regime_moderation_pilot`。

远端测试命令：

```bash
cd /home/lenovo/code/regime_moderation_pilot
PYTHONPATH=pilot/src /home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python -m unittest discover -s tests -v
```

最新结果：

```text
Ran 24 tests in 0.005s
OK
```

## Retrieval-side 结果

远端已复现 retrieval-side pilot：

`pilot/results/retrieval_metrics_remote.json`

此前本地结果：

```json
{
  "naive_memory": {
    "n": 10,
    "mean_invalid_activation_rate": 0.3,
    "mean_retrieved_count": 3.0
  },
  "policy_only": {
    "n": 10,
    "mean_invalid_activation_rate": 0.0,
    "mean_retrieved_count": 0.0
  },
  "regime_aware": {
    "n": 10,
    "mean_invalid_activation_rate": 0.0,
    "mean_retrieved_count": 3.0
  },
  "regime_filtered": {
    "n": 10,
    "mean_invalid_activation_rate": 0.0,
    "mean_retrieved_count": 3.0
  }
}
```

解释：

- 透明 retrieval 侧能看到 naive memory 会取到 invalid precedent。
- regime-aware selection 能把 invalid activation 降到 0。
- 但 retrieval-side 还不是完整 LLM agent 结果。

## LLM Agent Loop

新增代码：

- `pilot/src/regime_pilot/llm_pilot.py`
- `pilot/src/regime_pilot/ollama_client.py`
- `pilot/src/regime_pilot/run_llm_pilot.py`
- `tests/test_llm_pilot.py`
- `tests/test_run_llm_pilot.py`

设计：

- 用 Ollama HTTP API 调本地模型。
- agent 输出 JSON：`decision`、`rationale`、`used_precedents`。
- 评估 exact `policy_adherence`。
- 评估粗粒度 `decision_family_adherence`。
- 记录 `invalid_used_precedent_ids` 和 `unknown_used_precedent_ids`。

重要修正：

- 一开始 JSON schema 示例里写了具体 `R2-P-001`，导致模型在 `policy_only` 下也照抄 precedent id。
- 已修正为 `"used_precedents":[]`，并加入测试防止 prompt 示例污染。

## qwen2.5:7b 结果

最终远端结果：

`pilot/results/llm_qwen25_7b_10cases_4conds_final.json`

已拉回本地：

`pilot/results/llm_qwen25_7b_10cases_4conds_final.json`

摘要：

```json
{
  "policy_only": {
    "n": 10,
    "policy_adherence_rate": 0.5,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0,
    "mean_unknown_used_precedents": 0.0,
    "parse_error_rate": 0.0
  },
  "naive_memory": {
    "n": 10,
    "policy_adherence_rate": 0.8,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0,
    "mean_unknown_used_precedents": 0.0,
    "parse_error_rate": 0.0
  },
  "regime_filtered": {
    "n": 10,
    "policy_adherence_rate": 0.6,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0,
    "mean_unknown_used_precedents": 0.0,
    "parse_error_rate": 0.0
  },
  "regime_aware": {
    "n": 10,
    "policy_adherence_rate": 0.6,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0,
    "mean_unknown_used_precedents": 0.0,
    "parse_error_rate": 0.0
  }
}
```

当前解读：

- qwen2.5:7b 在这个 prompt 下没有显式使用 invalid precedent。
- coarse decision family 全部为 1.0，说明很多 exact label 错误其实是 `allow/contextualize` 或 `restrict/remove` 之间的细粒度差异。
- naive memory 的 exact policy adherence 从 0.5 提到 0.8，说明同一批 precedent 有 utility。
- 但当前 qwen2.5:7b 结果没有证明 naive memory 的跨 regime harm。

## llama3.2 结果

远端已跑：

`pilot/results/llm_llama32_10cases_4conds.json`

已拉回本地：

`pilot/results/llm_llama32_10cases_4conds.json`

摘要：

```json
{
  "policy_only": {
    "policy_adherence_rate": 0.4,
    "mean_invalid_used_precedents": 0.0
  },
  "naive_memory": {
    "policy_adherence_rate": 0.4,
    "mean_invalid_used_precedents": 0.1
  },
  "regime_filtered": {
    "policy_adherence_rate": 0.4,
    "mean_invalid_used_precedents": 0.0
  },
  "regime_aware": {
    "policy_adherence_rate": 0.4,
    "mean_invalid_used_precedents": 0.0
  }
}
```

关键污染案例：

- `T-002` 在 `naive_memory` 下引用了 `R2-P-002`。
- `R2-P-002` 对当前 `normal_civic_discussion_v1` 是 invalid precedent。
- 模型因此把明显讽刺从 expected `contextualize` 推到 `restrict`。

## Operational Memory v2 结果

新增 operational view：

- prompt 中保留当前 policy text。
- retrieved precedents 只展示自然操作信息：`case_id`、`post`、`decision`、`rationale`。
- 不向模型展示 precedent 的 `regime_id`、`validity_scope`、`compatible_regimes`、`retrieval_score`。
- transparent view 仍保留，用于 diagnostic。

本地和远端测试均已更新到 24 tests。

远端输出已拉回本地：

- `pilot/results/llm_qwen25_7b_10cases_4conds_operational.json`
- `pilot/results/llm_llama32_10cases_4conds_operational.json`

qwen2.5:7b operational 摘要：

```json
{
  "policy_only": {
    "policy_adherence_rate": 0.6,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0
  },
  "naive_memory": {
    "policy_adherence_rate": 0.7,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0
  },
  "regime_filtered": {
    "policy_adherence_rate": 0.6,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0
  },
  "regime_aware": {
    "policy_adherence_rate": 0.6,
    "decision_family_adherence_rate": 1.0,
    "mean_invalid_used_precedents": 0.0
  }
}
```

llama3.2 operational 摘要：

```json
{
  "policy_only": {
    "policy_adherence_rate": 0.5,
    "decision_family_adherence_rate": 0.7,
    "mean_invalid_used_precedents": 0.0
  },
  "naive_memory": {
    "policy_adherence_rate": 0.3,
    "decision_family_adherence_rate": 0.6,
    "mean_invalid_used_precedents": 0.2
  },
  "regime_filtered": {
    "policy_adherence_rate": 0.4,
    "decision_family_adherence_rate": 0.7,
    "mean_invalid_used_precedents": 0.0
  },
  "regime_aware": {
    "policy_adherence_rate": 0.5,
    "decision_family_adherence_rate": 0.7,
    "mean_invalid_used_precedents": 0.0
  }
}
```

当前解释：

- qwen2.5:7b 在 operational view 下仍然没有显式 invalid precedent use，说明强模型可能主动抵抗 stale examples。
- llama3.2 在 naive_memory 下出现 invalid precedent use，并伴随 family-level adherence 下降。
- regime_filtered / regime_aware 在 llama3.2 上把 invalid precedent use 降到 0。
- 因此当前 pilot 更适合支撑 “model-capability-dependent memory contamination risk”，而不是声称所有模型都会被跨 regime precedent 污染。

这个现象支持 cross-regime contamination，但只在较小模型上明显。强模型 qwen2.5:7b 当前 prompt 下没有出现。

## 当前结论

这次 4090 pilot 给出一个清楚的方向判断：

1. 远端环境可用，Ollama 路线可行。
2. retrieval-side naive contamination 信号存在。
3. LLM-side contamination 在较弱模型上出现。
4. 较强模型在显式 policy + 显式 compatible metadata prompt 下较稳，会主动避开 invalid precedent。
5. 当前实验还不足以支撑最终论文主张，需要把任务改得更接近真实长期 memory：
   - naive memory 不应直接暴露 `compatible_regimes`。
   - policy 文本应更简短、欠规定。
   - precedent utility 应通过边界案例拉开。
   - 应增加 implicit/partial regime setting。
   - 应评估 stale rationale，而不只看 explicit `used_precedents`。

## 下一步建议

下一版实验应做两个 prompt/memory setting：

1. **Transparent setting**：继续暴露 `regime_id`、`validity_scope`、`compatible_regimes`，用于诊断。
2. **Operational memory setting**：naive memory 只给 case text、decision、rationale，不给 compatibility metadata；regime-aware memory 才经过过滤。

如果 qwen2.5:7b 在 operational memory setting 下出现：

- same-regime utility 提升；
- cross-regime stale rationale 或 invalid precedent use；
- regime-aware 降低 contamination；

这个方向就更值得扩大到 60 cases。
