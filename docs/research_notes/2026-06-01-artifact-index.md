# Artifact Index

日期：2026-06-01

这个文件记录 Regime-aware Moderation Memory 规划阶段已经落盘的研究材料。

## 主规格文档

`docs/superpowers/specs/2026-06-01-regime-aware-moderation-memory-pilot-design.md`

用途：

- 定义 v2 pilot。
- 规定研究问题、regime setup、数据 schema、实验条件、指标、成功标准和实现预览。
- 这是后续 implementation plan 的 source of truth。

## 旧 Pilot 审计

`docs/research_notes/2026-06-01-claude-pilot-audit.md`

用途：

- 总结 Claude 旧 pilot 做了什么。
- 解释为什么旧 pilot 没有回答当前研究问题。
- 记录可复用教训：不要 Mem0-first、不要关键词评估、必须包含 within-regime memory utility。

## 方向快照

`docs/research_notes/2026-06-01-direction-snapshot.md`

用途：

- 记录当前最佳论文方向。
- 解释为什么 DynaGuard 没有完全覆盖。
- 列出主要风险和 fallback directions。

## 现有本地输入

`iclr2025_conference.tex`

用途：

- 当前论文初稿。
- 有价值的核心 insight：semantic relevance does not imply regime validity。
- 后续要修正的主要问题：当前 RAM-minimal framing 在 explicit regimes 下容易像 metadata filtering。

`claudecode.result`

用途：

- Claude 讨论和旧 pilot 日志。
- 可作为 negative/diagnostic pilot history。

`papers/`

用途：

- 本地 related-work 集合。
- 相关压力点包括 DynaGuard、STITCH、GLOVE、CMI、hierarchical alignment、value conflict 和 memory-management papers。

## 下一份预期 artifact

用户确认后，创建 pilot implementation plan。推荐路径：

`docs/superpowers/plans/2026-06-01-regime-aware-moderation-memory-pilot-implementation.md`

## 已创建的实现 artifact

Implementation plan：

`docs/superpowers/plans/2026-06-01-regime-aware-moderation-memory-pilot-implementation.md`

Pilot 数据：

- `pilot/data/policies.json`
- `pilot/data/precedents.jsonl`
- `pilot/data/test_cases.jsonl`

Pilot 代码：

- `pilot/src/regime_pilot/schema.py`
- `pilot/src/regime_pilot/retrieval.py`
- `pilot/src/regime_pilot/conditions.py`
- `pilot/src/regime_pilot/evaluate.py`
- `pilot/src/regime_pilot/run_pilot.py`

Pilot 测试：

- `tests/test_schema.py`
- `tests/test_retrieval.py`
- `tests/test_conditions.py`
- `tests/test_evaluate.py`
- `tests/test_run_pilot.py`

Pilot 结果：

`pilot/results/retrieval_metrics.json`

实现状态记录：

`docs/research_notes/2026-06-01-pilot-implementation-status.md`

数据种子备忘：

`docs/research_notes/2026-06-01-pilot-data-seed-notes.md`

4090 远端运行记录：

`docs/research_notes/2026-06-02-remote-gpu-run.md`

LLM pilot 代码：

- `pilot/src/regime_pilot/llm_pilot.py`
- `pilot/src/regime_pilot/ollama_client.py`
- `pilot/src/regime_pilot/run_llm_pilot.py`

LLM pilot 测试：

- `tests/test_llm_pilot.py`
- `tests/test_run_llm_pilot.py`

LLM pilot 本地结果：

- `pilot/results/llm_smoke_llama32_3cases_v2.json`
- `pilot/results/llm_smoke_qwen25_7b_3cases.json`
- `pilot/results/llm_qwen25_7b_10cases_4conds_final.json`
- `pilot/results/llm_llama32_10cases_4conds.json`
- `pilot/results/llm_qwen25_7b_10cases_4conds_operational.json`
- `pilot/results/llm_llama32_10cases_4conds_operational.json`

Operational Memory v2 研究备忘：

`docs/research_notes/2026-06-02-operational-memory-v2-plan.md`

Operational Memory v2 运行记录：

`docs/research_notes/2026-06-02-operational-memory-v2-run.md`

qwen2.5 stress test implementation plan：

`docs/superpowers/plans/2026-06-02-qwen-stress-test-implementation.md`

qwen2.5 stress test 运行记录：

`docs/research_notes/2026-06-02-qwen-stress-test-run.md`

qwen2.5 stress test 结果：

- `pilot/results/llm_qwen25_7b_stress_full_warning_on.json`
- `pilot/results/llm_qwen25_7b_stress_full_warning_off.json`
- `pilot/results/llm_qwen25_7b_stress_brief_warning_on.json`
- `pilot/results/llm_qwen25_7b_stress_brief_warning_off.json`

Case-guidance gap 问题定义备忘：

`docs/research_notes/2026-06-03-case-guidance-gap-problem-definition.md`

Case-guidance mini-study implementation plan：

`docs/superpowers/plans/2026-06-03-case-guidance-mini-study-implementation.md`

Case-guidance mini-study 数据：

- `pilot/data/mini_case_guidance_cases.jsonl`
- `pilot/data/mini_case_guidance_precedents.jsonl`
- `pilot/data/mini_case_guidance_stale_precedents.jsonl`
- `pilot/data/mini_case_guidance_current_precedents.jsonl`

Case-guidance mini-study 结果：

- `pilot/results/llm_qwen25_7b_case_guidance_mini_brief_off.json`
- `pilot/results/llm_qwen25_7b_case_guidance_mini_stale_pool_brief_off.json`
- `pilot/results/llm_qwen25_7b_case_guidance_mini_current_pool_brief_off.json`
- `pilot/results/llm_llama32_case_guidance_mini_brief_off.json`

Case-guidance mini-study 运行记录：

`docs/research_notes/2026-06-03-case-guidance-mini-study-run.md`

Case-guidance gap 领导汇报说明：

`docs/research_notes/2026-06-03-case-guidance-gap-leadership-brief.md`

Policy Boundary Gap 问题备忘：

`docs/research_notes/2026-06-04-policy-boundary-gap-problem-memo.md`

## 2026-06-08 Boundary Sufficiency Pilot 研究设计

`docs/research_notes/2026-06-08-policy-boundary-sufficiency-study-design.md`

用途：

- 定义 Boundary Sufficiency Pilot 的研究定位：policy specification testing / diagnostic boundary probes，而不是更好的 BARRED 合成训练数据。
- 区分 BARRED、DynaGuard、instruction following 与本研究的边界。
- 记录 RQ、boundary family、实验条件、指标和不主张的 claim 边界。

## 2026-06-08 Boundary Sufficiency Pilot 数据、代码与结果

Boundary sufficiency 数据：

- `pilot/data/boundary_sufficiency_cases.jsonl`
- `pilot/data/boundary_sufficiency_guidance_current.jsonl`
- `pilot/data/boundary_sufficiency_guidance_stale.jsonl`

Boundary sufficiency analyzer：

- `pilot/src/regime_pilot/analyze_boundary_sufficiency.py`
- `tests/test_analyze_boundary_sufficiency.py`

远端运行与结果备忘：

`docs/research_notes/2026-06-08-boundary-sufficiency-pilot-run.md`

关键聚合结果：

- `pilot/results/remote_20260608_boundary_sufficiency_main_analysis_no_qwen3.json`
- `pilot/results/remote_20260608_boundary_sufficiency_full_on_analysis.json`

用途：

- 记录 12 个 diagnostic boundary probes 的远端 4090 运行结果。
- 汇总 qwen2.5:7b、llama3.2、qwen2.5:14b、qwen3:14b 的表现。
- 标注 qwen3:14b 的 parse failure 风险，并将主分析排除 qwen3。

用途：

- 将当前主线从 case-guidance gap 上移到 policy boundary gap。
- 明确三类边界：真实政策边界、文本政策边界、模型执行边界。
- 解释 DynaGuard、BARRED、OpenAI moderation practice 与我们问题的关系。
- 记录下一步问题确认型 study 的目标。

## 2026-06-08 clarified policy 与 BARRED-like 后续实验

clarified policy patch：

- `pilot/data/boundary_sufficiency_policies_clarified.json`

BARRED-like 前半段审计代码：

- `pilot/src/regime_pilot/barred_like.py`
- `tests/test_barred_like.py`

abstract vs clarified 对照比较器：

- `pilot/src/regime_pilot/compare_boundary_sufficiency.py`
- `tests/test_compare_boundary_sufficiency.py`

远端复跑脚本：

- `scripts/run_2026_06_08_next_boundary_experiments.ps1`

结果分析模板：

- `docs/research_notes/2026-06-08-clarified-policy-and-barred-like-next-step-plan.md`

本轮推进状态：

- `docs/research_notes/2026-06-08-next-boundary-experiment-status.md`

本轮运行结果：

- `docs/research_notes/2026-06-08-next-boundary-experiment-run.md`
- `docs/research_notes/2026-06-08-education-extended-anchor-run.md`

education/critique 扩展数据：

- `pilot/data/boundary_sufficiency_cases_education_extended.jsonl`
- `pilot/data/boundary_sufficiency_guidance_current_education_extended.jsonl`
- `pilot/data/boundary_sufficiency_guidance_stale_education_extended.jsonl`
- `tests/test_boundary_sufficiency_education_extended_data.py`

BARRED-like anchor overlay：

- `pilot/data/barred_like_anchor_review_qwen25_7b_20260608.jsonl`
- `pilot/src/regime_pilot/analyze_barred_like_anchor_review.py`
- `tests/test_analyze_barred_like_anchor_review.py`

education/anchor 远端复跑脚本：

- `scripts/run_2026_06_08_education_anchor_experiments.ps1`

education/anchor 关键结果：

- `pilot/results/remote_20260608_education_ext_abstract_full_on_analysis.json`
- `pilot/results/remote_20260608_education_ext_clarified_full_on_analysis.json`
- `pilot/results/remote_20260608_education_ext_abstract_vs_clarified_full_on_comparison.json`
- `pilot/results/remote_20260608_barred_like_anchor_review_qwen25_7b_analysis.json`

用途：

- 回应「policy 写清楚即可」的质疑：通过 abstract policy vs clarified policy 对照测试 gap 是否下降。
- 回应「BARRED 已经做 synthetic data/debate」的质疑：只审计 synthetic/debate 前半段是否产生 high-agreement / low-anchor 的伪边界候选。
- 记录 4090 远端当前 SSH 不可达，以及恢复后的可复跑命令。
- 记录扩展后的关键观察：category boundary 与 action granularity 需要分开评估；clarified policy 可以消除 decision-family error，但仍可能留下 exact action label error。
