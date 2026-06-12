# clarified policy 与 BARRED-like 下一步实验推进状态

日期：2026-06-08

## 本轮目标

本轮只推进两个最关键的验证，不扩数据集规模：

1. `clarified policy patch` 对照：回答「如果 policy 写清楚，是不是 gap 就会下降」。
2. `BARRED-like synthetic/debate` 前半段审计：回答「数据生成 + judge/debate 是否可能在抽象 policy 下形成伪边界一致」。

这两步共同服务一个论文判断：

> Boundary Sufficiency 的价值不是替代好 policy，也不是替代 BARRED-like synthetic data，而是在生成、筛选、训练边界样本之前，先测试 policy text 是否足以规定这些边界。

## 已完成

### 1. clarified policy patch 已落盘

文件：

- `pilot/data/boundary_sufficiency_policies_clarified.json`

这个文件保留原有两个 regime：

- `normal_civic_discussion_v1`
- `election_integrity_period_v2`

但把四个 boundary family 的规则写得更明确：

- `future_reform_vs_current_voting_instruction`
- `obvious_satire_vs_deceptive_notice`
- `prediction_opinion_vs_false_certification`
- `education_critique_quote_vs_endorsement_or_mobilization`

关键控制点：

- 没有覆盖原始 `pilot/data/policies.json`。
- 没有把具体 probe post 塞进 policy，避免泄漏测试样本。
- 只补 boundary variable 和 exception，不重写整个任务。

### 2. prompt formatter 已修复

文件：

- `pilot/src/regime_pilot/llm_pilot.py`

原因：

clarified policy 使用嵌套结构表示规则。如果 formatter 仍按字符串处理，LLM prompt 中会出现 Python dict repr，例如单引号和不稳定结构。这会污染 clarified policy 对照，因为模型没有以规范文本形式看到 policy。

修复：

- 字符串规则保持原样。
- 嵌套规则用稳定 JSON 格式进入 prompt。
- 新增测试确认 nested rules 可读且不出现 Python repr。

### 3. BARRED-like 前半段 runner 已落盘

文件：

- `pilot/src/regime_pilot/barred_like.py`
- `tests/test_barred_like.py`

它现在支持：

- 从指定 policy regime 生成 diagnostic boundary candidates。
- 指定 `--regime-id`，避免默认拿到错误 regime。
- 指定 `--judge-count` 与 `--judge-variants`，用不同 judge prompt variants 做前半段审计。
- 记录 judge 配置，避免把同模型同 prompt 的确定性重复误写成独立 judge agreement。
- 输出 `generated_candidates`、`invalid_candidates`、`generation_errors`、`judge_results`、`judge_errors`、`summaries`、`pseudo_consensus_candidates`、`manual_review_candidates`。
- generator 或 judge 返回 malformed JSON 时不中止整个审计，而是记录 raw response 与 parse error，方便人工复核。

注意：

这个 runner 不是 BARRED 复现，也不做微调。它只审计 synthetic/debate 前半段是否会在抽象 policy 下形成高一致但缺少 current-policy anchor 的候选边界。

口径必须保守：

- `pseudo_consensus_candidates` 只有在 candidate 含有外部 anchor label，且多个 prompt-variant judgments 一致冲突该 anchor 时才出现。
- 如果没有外部 anchor，只能进入 `manual_review_candidates`，不能 claim 伪一致。
- 当前默认的 `policy_clause,boundary_variable` 是 prompt-variant judging，不是完整 debate。

### 4. 远端复跑脚本已落盘

文件：

- `scripts/run_2026_06_08_next_boundary_experiments.ps1`

脚本内容：

- 同步 `docs/`、`pilot/`、`tests/`、`scripts/` 到 4090 远端。
- 运行远端 unittest。
- 跑 clarified policy full/on 对照：
  - `qwen2.5:7b`
  - `llama3.2:latest`
  - current guidance pool
  - stale guidance pool
- 聚合 clarified 结果。
- 重新聚合 abstract full/on baseline，并生成 abstract-vs-clarified delta comparison。
- 跑 BARRED-like 4-family 小样本审计：
  - `qwen2.5:7b`
  - 每个 family 2 个 candidates
  - 2 个 judge prompt variants：`policy_clause`、`boundary_variable`
- 把结果拉回本地 `pilot/results/`。

恢复远端后运行：

```powershell
.\scripts\run_2026_06_08_next_boundary_experiments.ps1
```

### 5. 本地验证已通过

本地验证命令：

```powershell
$env:PYTHONPATH='pilot/src'
& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -v
```

结果：

- 42 tests
- 后续修订后为 46 tests
- 0 failures
- 0 errors

另外做过两个红绿验证：

- nested policy rule formatter：先失败，再修复通过。
- BARRED-like CLI `--regime-id` / `--judge-count`：先失败，再修复通过。
- BARRED-like anchor-aware metrics / parse error 记录：先失败，再修复通过。
- abstract-vs-clarified comparison：先失败，再修复通过。

## 当前阻塞

4090 远端当前不可达。

检测结果：

- `ssh lenovo@10.147.18.151 "pwd"` 超时。
- `Test-NetConnection 10.147.18.151 -Port 22` 显示：
  - `PingSucceeded: False`
  - `TcpTestSucceeded: False`
  - 接口：`ZeroTier One`
  - 本机 ZeroTier 地址：`10.147.18.78`

因此当前不是实验代码阻塞，而是远端网络/主机连接阻塞。

## 远端恢复后需要看的结果

### clarified policy 对照

预期新增文件：

- `pilot/results/remote_20260608_qwen25_7b_boundary_current_clarified_full_on.json`
- `pilot/results/remote_20260608_qwen25_7b_boundary_stale_clarified_full_on.json`
- `pilot/results/remote_20260608_llama32_boundary_current_clarified_full_on.json`
- `pilot/results/remote_20260608_llama32_boundary_stale_clarified_full_on.json`
- `pilot/results/remote_20260608_boundary_sufficiency_abstract_full_on_analysis_for_compare.json`
- `pilot/results/remote_20260608_boundary_sufficiency_clarified_full_on_analysis.json`
- `pilot/results/remote_20260608_boundary_sufficiency_abstract_vs_clarified_full_on_comparison.json`

需要和已有 abstract full/on 对照：

- `pilot/results/remote_20260608_boundary_sufficiency_full_on_analysis.json`

重点看：

- `policy_only_boundary_error_rate` 是否下降。
- `boundary_instability_rate` 是否下降。
- `current_guidance_rescue_rate` 是否下降。
- 哪些 family 被 clarified policy 修复，哪些没有。

解释规则：

- 如果 clarified policy 明显改善：说明「policy 写清楚」确实有用，而我们的贡献是诊断哪里没写清楚。
- 如果 clarified policy 不改善：说明问题不只是 wording，可能是 instruction following、prompt format 或 boundary 本身仍需 policy-owner anchor。

### BARRED-like 前半段审计

预期新增文件：

- `pilot/results/remote_20260608_barred_like_qwen25_7b_4families_2candidates.json`

重点看：

- 每个 family 生成了多少 candidates。
- judge agreement 是否高。
- `pseudo_consensus_candidates` 是否出现。
- `manual_review_candidates` 是否出现。
- `judge_agreement_basis` 是否为 `prompt_variants`。
- `generation_errors` 和 `judge_errors` 是否说明结果可用。
- flagged candidate 是否真是 policy 未规定的边界，还是低质量生成/parse bug。

解释规则：

- 如果出现 high agreement / low anchor：可以主张 synthetic/debate 前半段需要 policy sufficiency audit。
- 如果没有出现 pseudo-consensus：不能批评 BARRED-like 伪一致，论文主线应回到 preflight diagnostic。
- 如果只出现 `manual_review_candidates`：只能说这些候选值得人工 anchor 复核，不能说已经发现伪一致。

## 当前论文判断

在远端新实验未跑之前，当前已有结果仍然支持继续推进 Boundary Sufficiency，但不能新增 BARRED-like 相关强 claim。

目前可以稳妥说：

- abstract policy 下存在可观测 boundary instability。
- current guidance 有 rescue 信号。
- stale/data-first guidance 有 harm 信号。
- 下一步最关键不是扩数据，而是确认 clarified policy 是否修复 gap，以及 synthetic/debate 是否有伪一致风险。

目前不能说：

- BARRED 错。
- debate 一定制造伪边界。
- clarified policy 一定能解决问题。
- Boundary Sufficiency 已经有完整方法闭环。

## 下一步执行顺序

1. 等远端 SSH 恢复。
2. 运行 `scripts/run_2026_06_08_next_boundary_experiments.ps1`。
3. 读取 clarified analysis，与 abstract full/on 结果做表格对比。
4. 人工复核 BARRED-like flagged candidates。
5. 写最终结果 memo，判断路线：
   - 继续 Boundary Sufficiency。
   - 转向 BARRED reliability audit。
   - 回退到问题定义/实验设计重构。
