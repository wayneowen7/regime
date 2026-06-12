# Boundary Sufficiency Pilot 运行记录与初步判断

日期：2026-06-08

## 结论摘要

本轮 pilot 已经把研究问题从「更好的 BARRED 式合成数据」推进到「policy specification testing」。我们新增了 12 个 matched boundary probes，并在远端 4090 上用多个本地模型测试 `policy_only`、`naive_memory` 和 `regime_aware` 三类 operationalization 条件。

当前最重要的初步结论是：

> Policy Boundary Sufficiency 是可观测的：在相同 policy text 下，模型会在 boundary probes 上形成不稳定边界；current-policy-valid guidance 能显著 rescue 一部分错误；stale/data-first guidance 会把部分判断推向旧边界。

这不是最终论文结论，但已经足够支持继续扩展该方向。

## 本轮新增产物

研究设计：

- `docs/research_notes/2026-06-08-policy-boundary-sufficiency-study-design.md`

数据：

- `pilot/data/boundary_sufficiency_cases.jsonl`
- `pilot/data/boundary_sufficiency_guidance_current.jsonl`
- `pilot/data/boundary_sufficiency_guidance_stale.jsonl`

代码：

- `pilot/src/regime_pilot/analyze_boundary_sufficiency.py`
- `tests/test_analyze_boundary_sufficiency.py`

远端结果：

- `pilot/results/remote_20260608_qwen25_7b_boundary_current_brief_off.json`
- `pilot/results/remote_20260608_qwen25_7b_boundary_stale_brief_off.json`
- `pilot/results/remote_20260608_qwen25_7b_boundary_mixed_brief_off.json`
- `pilot/results/remote_20260608_llama32_boundary_current_brief_off.json`
- `pilot/results/remote_20260608_llama32_boundary_stale_brief_off.json`
- `pilot/results/remote_20260608_llama32_boundary_mixed_brief_off.json`
- `pilot/results/remote_20260608_qwen25_14b_boundary_current_brief_off_12case.json`
- `pilot/results/remote_20260608_qwen25_14b_boundary_stale_brief_off_12case.json`
- `pilot/results/remote_20260608_qwen3_14b_boundary_current_brief_off_12case.json`
- `pilot/results/remote_20260608_qwen3_14b_boundary_stale_brief_off_12case.json`
- `pilot/results/remote_20260608_qwen25_7b_boundary_current_full_on.json`
- `pilot/results/remote_20260608_qwen25_7b_boundary_stale_full_on.json`
- `pilot/results/remote_20260608_llama32_boundary_current_full_on.json`
- `pilot/results/remote_20260608_llama32_boundary_stale_full_on.json`

聚合结果：

- `pilot/results/remote_20260608_boundary_sufficiency_phase1_analysis.json`
- `pilot/results/remote_20260608_boundary_sufficiency_combined_analysis.json`
- `pilot/results/remote_20260608_boundary_sufficiency_full_on_analysis.json`
- `pilot/results/remote_20260608_boundary_sufficiency_main_analysis_no_qwen3.json`

## 数据设计

本轮新增 12 个 probes，覆盖 4 个 boundary family：

1. `future_reform_vs_current_voting_instruction`
2. `obvious_satire_vs_deceptive_notice`
3. `prediction_opinion_vs_false_certification`
4. `education_critique_quote_vs_endorsement_or_mobilization`

每个 family 有 3 个 matched probes。每条 probe 的 `expected_rationale` 中记录：

- `boundary_family`
- `hidden_anchor_label`
- `anchor_rationale`

这些字段用于 analyzer 聚合，但不会进入 LLM prompt。这样能保持现有 schema 兼容，同时让分析层按 boundary family 汇总。

## 实验设置

远端环境：

- 服务器：`lenovo@10.147.18.151`
- 工作目录：`/home/lenovo/code/regime_boundary_sufficiency`
- Python：`/home/lenovo/code/miniconda3/bin/conda run -n unsloth_env python`

已验证：

- 远端 unittest：31 tests，OK。
- qwen2.5:7b 与 llama3.2 的 1-case LLM smoke 均成功。

主要模型：

- `qwen2.5:7b`
- `llama3.2:latest`
- `qwen2.5:14b`
- `qwen3:14b`

注意：`qwen3:14b` 在本 prompt 下出现严重 JSON parse failure，72 行中 66 行 parse error。因此主分析排除了 qwen3，把它作为 prompt/format robustness 风险记录。

## 主分析结果

主分析文件：

`pilot/results/remote_20260608_boundary_sufficiency_main_analysis_no_qwen3.json`

输入包括：

- qwen2.5:7b brief/off：current、stale、mixed
- llama3.2 brief/off：current、stale、mixed
- qwen2.5:14b brief/off：current、stale
- qwen2.5:7b full/on：current、stale
- llama3.2 full/on：current、stale

整体结果：

| 指标 | 数值 |
|---|---:|
| `n_cases` | 12 |
| `n_rows` | 432 |
| `policy_only_boundary_error_rate` | 0.479 |
| `current_guidance_rescue_rate` | 1.000 |
| `stale_guidance_harm_rate` | 0.833 |
| `boundary_instability_rate` | 0.750 |
| `invalid_used_precedent_rate` | 0.049 |
| `stale_rationale_match_total` | 25 |
| `pseudo_consensus_candidates` | 0 |

分 family 结果：

| boundary family | policy-only error | rescue | stale harm | instability |
|---|---:|---:|---:|---:|
| future reform vs current instruction | 0.250 | 1.000 | 1.000 | 0.667 |
| obvious satire vs deceptive notice | 0.528 | 1.000 | 1.000 | 1.000 |
| prediction/opinion vs false certification | 0.528 | 1.000 | 0.667 | 0.667 |
| education/critique vs endorsement/mobilization | 0.611 | 1.000 | 0.667 | 0.667 |

## full/on 对照

full policy + stale warning on 的单独分析文件：

`pilot/results/remote_20260608_boundary_sufficiency_full_on_analysis.json`

结果：

| 指标 | 数值 |
|---|---:|
| `n_cases` | 12 |
| `n_rows` | 144 |
| `policy_only_boundary_error_rate` | 0.500 |
| `current_guidance_rescue_rate` | 0.900 |
| `stale_guidance_harm_rate` | 0.800 |
| `boundary_instability_rate` | 0.667 |
| `invalid_used_precedent_rate` | 0.049 |
| `stale_rationale_match_total` | 10 |

解读：

- full/on 没有消除 gap，但 `boundary_instability_rate` 相比混合主分析有所下降。
- 这说明「更完整 policy + stale warning」有帮助，但不足以让 boundary probes 完全稳定。
- 因为本轮 full/on 只覆盖 qwen2.5:7b 和 llama3.2，不应过度推广。

## 代表性观察

### 1. policy-only 不足在多个 family 中出现

主分析中 `policy_only_boundary_error_rate = 0.479`。这不是单个模型失误，而是在多个模型、多个 family、多个 presentation 中都可观察。

尤其是：

- `education_critique_quote_vs_endorsement_or_mobilization`：0.611
- `prediction_opinion_vs_false_certification`：0.528
- `obvious_satire_vs_deceptive_notice`：0.528

这支持一个温和但重要的 claim：

> 对 boundary probes 来说，当前 policy text 并不总是足以稳定指定可执行边界。

### 2. current guidance 有明显 rescue 信号

主分析中 `current_guidance_rescue_rate = 1.000`。

这说明当 policy-only 在某些 boundary probe 上出错时，current-policy-valid guidance 能把判断拉回 expected boundary。它支持方法空间：

> boundary clarification 不需要大规模样本；少量 current-valid boundary guidance 就可能显著修复 under-specified policy 的执行边界。

### 3. stale/data-first guidance 有 harm 信号

主分析中 `stale_guidance_harm_rate = 0.833`，并且存在显式 invalid precedent use：

`invalid_used_precedent_rate = 0.049`

这说明语义相关但 current-policy-invalid 的 guidance 会在部分 probes 上造成边界移动。注意这个指标不应被写成「历史案例总是污染」，而应写成：

> 当 guidance source 未区分 current-valid 与 stale/invalid 时，data-first operationalization 会把部分边界推向旧 regime。

### 4. pseudo-consensus 暂未出现

本轮 `pseudo_consensus_candidates = []`。

这不是坏事，说明第一版 pilot 更强地支持了：

- policy-only insufficiency
- current guidance rescue
- stale guidance harm
- boundary instability

但还没有支持「BARRED-like debate 形成伪一致」这一 claim。下一轮如果要写 BARRED 相关主张，需要专门实现 debate/synthetic generation 对照，而不能用当前结果直接 claim pseudo-consensus。

### 5. qwen3:14b 暂时不可作为 substantive evidence

`qwen3:14b` 在 brief/off 条件下 72 行输出中 66 行 parse error。

可能原因：

- 模型输出格式不稳定；
- JSON-only prompt 对 qwen3 系列不够强；
- 可能有额外 reasoning / non-JSON 包裹没有被 parser 捕获。

当前处理：

- qwen3 结果保留为 robustness 风险记录；
- 主分析排除 qwen3，避免 parse error 抬高 instability。

## 当前验收状态

计划中的研究验收条件：

1. 至少 2 个 boundary family 能展示 policy-only 或 data-first 的边界不稳定。
2. 至少 1 个 case 展示 current guidance rescue。
3. 至少 1 个 case 展示 stale/data-first harm 或 pseudo-consensus candidate。

当前结果：

- 条件 1：满足。4 个 family 都有 instability，主分析 overall 0.750。
- 条件 2：满足。current guidance rescue overall 1.000。
- 条件 3：满足。stale guidance harm overall 0.833；pseudo-consensus 暂未出现。

因此本轮 pilot 达到继续推进的门槛。

## 不能 claim 什么

本轮不能 claim：

- 不能 claim BARRED 错。
- 不能 claim debate 一定产生伪边界。
- 不能 claim policy-only 普遍失败。
- 不能 claim qwen3 在任务上差，因为当前主要是 parse/format 失败。
- 不能 claim `stale_rationale_match_total` 等于真实污染率；它只是 triage signal。
- 不能 claim 12 个 probes 足以支撑论文主实验。

## 下一步建议

下一步不要急着扩到 100 条数据。建议先做两个更关键的动作：

1. **实现 BARRED-like synthetic/debate 前半段对照**
   - 从同一 policy text 自动生成 candidate boundary cases。
   - 用 2-3 个 judge/debate prompts 给 label。
   - 测量 sample yield、agreement、anchor agreement。
   - 目标是直接测试 pseudo-consensus，而不是泛泛批评 BARRED。

2. **强化 clear-policy 对照**
   - 为 4 个 family 写显式 clarified policy patch。
   - 比较 abstract policy vs clarified policy。
   - 如果 clarified policy 明显降低 error/instability，就能更有力回应「policy 写清楚即可」：
     - 是的，写清楚有用；
     - 我们研究的是如何发现哪里还没写清楚。

如果这两个后续实验成立，论文主线会很稳：

> Before synthetic guardrail training, test whether the policy sufficiently specifies the boundary to be synthesized.
