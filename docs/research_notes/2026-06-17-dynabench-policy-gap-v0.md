# DynaBench Policy Gap V0 运行记录

## 为什么切到 DynaBench

当前主线研究问题是 policy-to-operation gap：给定自然语言 policy，模型是否能稳定执行到正确的审核操作；如果不能，boundary clarification 和 action rubric 是否能降低错误。

因此 v0 主数据必须同时满足：

1. 有自然语言 policy text；
2. 有待判断 case/input；
3. 有 ground-truth decision；
4. policy 与 label 之间有可解释对应关系。

DynaBench 满足这个硬条件：每条记录包含 `policy`、`transcript`、`label`。Aegis 2.0 虽然是内容安全数据集，但缺少逐条 policy text，所以暂时不作为主线 v0。

## V0 数据构造

输入：

- `data/raw/dataset_bootstrap/dynabench_sample500.jsonl`

输出 raw artifacts：

- `data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_cases_v0.jsonl`
- `data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_policies_abstract.json`
- `data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_policies_boundary.json`
- `data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_policies_action_rubric.json`
- `data/raw/dynabench_policy_gap_v0/dynabench_policy_gap_empty_precedents.jsonl`

这些文件包含第三方 policy/transcript 文本，只保留在 `data/raw/`，不进入 git。

Text-free summary：

- `pilot/results/dynabench_policy_gap_v0_summary.json`

V0 抽样：

- 100 cases
- PASS: 50
- FAIL: 50
- expected action:
  - PASS -> `allow`
  - FAIL -> `remove`

这个映射是 v0 的 operational projection，不声称是 DynaBench 原生 action label。

## 三层 policy view

### Abstract Policy

只保留高层合规意图：模型需要判断 transcript 是否满足 policy goal，但不提供原始 policy 边界。

目的：制造 policy-to-operation gap 的低信息条件。

### Boundary Policy

提供原始 DynaBench policy text，作为真实操作边界。

目的：测试给出具体 policy 后，模型是否降低 coarse decision-family error。

### Action Rubric Policy

在原始 policy text 之后加上动作映射：

- transcript follows policy -> `allow`
- transcript violates policy -> `remove`

目的：测试在边界之外加入显式操作动作后，是否降低 exact-action error。

## 远端 10-case smoke

远端环境：

- host: `lenovo@10.147.18.151`
- models: `qwen2.5:7b`, `llama3.2:latest`
- each run: first 10 cases, `policy_only`, `top_k=0`

结果摘要：

- `pilot/results/dynabench_policy_gap_v0_10case_smoke_summary.json`
- raw model outputs are kept locally under `data/raw/dynabench_policy_gap_v0/llm_outputs/` and are not committed, because rationales may repeat snippets from third-party policy or transcript text.

### 初步信号

qwen2.5:7b：

- abstract exact/action adherence: 0.4
- boundary exact adherence: 0.2; family adherence: 0.6
- action rubric exact/family adherence: 0.8

解释：abstract 条件下 qwen 倾向全部 `allow`；加入 action rubric 后，模型开始执行 `FAIL -> remove` 的操作映射，出现正向信号。

llama3.2：

- abstract exact/family adherence: 0.7
- boundary exact adherence: 0.6; family adherence: 0.8
- action rubric exact/family adherence: 0.6

解释：llama 在 action rubric 下倾向全部 `remove`，说明当前 rubric 对部分模型可能诱发 over-removal，需要后续校准。

## 当前判断

这次只证明管线跑通，并提供很小的机制信号，不能当论文结论。

更重要的是，DynaBench-only v0 解决了此前 Aegis 设计中的根本问题：它保留了 policy-native 结构，因此真正对应 policy-to-operation gap，而不是无 policy 数据集上的普通安全分类。

## 下一步

建议下一步不要马上扩展到 Aegis/BARRED，而是先在 DynaBench 上做两个修正：

1. 用 30-50 cases 复跑 qwen/llama，确认 10-case 信号是否稳定；
2. 校准 action rubric，避免对 llama 这种模型产生 “all remove” 偏置。

如果 DynaBench 30-50 case 仍显示 boundary/rubric 层次有稳定收益，再扩展到 BARRED 做外部对照。
