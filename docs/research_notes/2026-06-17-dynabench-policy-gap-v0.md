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

## Action Rubric V2 校准

旧版 action rubric 的问题是只强调 `FAIL -> remove`，容易让某些模型把严格 policy 理解成默认高压删除。10-case smoke 中，llama3.2 在 action rubric 下预测为全 `remove`，说明 rubric 本身会诱发 over-removal。

V2 改动：

- 明确本 benchmark 只使用 `allow` / `remove` 两个动作；
- 显式写出 `PASS -> allow` 与 `FAIL -> remove` 的对称映射；
- 增加保护条件：不要因为 policy 严格、内容复杂、或者保守选择看起来更安全就删除；
- 要求模型先识别具体满足或违反的 policy requirement，再选择动作。

### 30-case smoke

远端环境：

- host: `lenovo@10.147.18.151`
- models: `qwen2.5:7b`, `llama3.2:latest`
- each run: first 30 cases, `policy_only`, `top_k=0`

Text-free summary:

- `pilot/results/dynabench_policy_gap_v0_action_rubric_v2_30case_summary.json`

qwen2.5:7b：

- abstract exact adherence: 0.4333
- boundary exact adherence: 0.2667; family adherence: 0.7000
- action_rubric_v2 exact/family adherence: 0.7333
- interpretation: v2 相比 abstract 的 exact adherence 提升 +0.3000。

llama3.2：

- abstract exact/family adherence: 0.5000
- boundary exact adherence: 0.3667; family adherence: 0.6667
- action_rubric_v2 exact/family adherence: 0.6333
- interpretation: v2 相比 abstract 的 exact adherence 提升 +0.1333，并且不再出现旧版 action rubric 的 all-remove 行为。

### 当前判断

V2 的信号比旧版更健康：它同时保留了 qwen 上的明显收益，并缓解了 llama 的全删除偏置。更重要的是，结果符合我们的方法假设：

- abstract policy 容易诱发模型默认策略偏置；
- boundary policy 帮助模型理解 policy，但可能仍输出非目标动作，如 `contextualize` 或 `restrict`；
- action rubric 把 policy boundary 绑定到操作动作后，提高 exact-action adherence。

当前仍然只是 30-case smoke。下一步应在 DynaBench 上扩展到 100 cases，并加入对 `allow -> remove` 与 `remove -> allow` 两类错误的细分分析。

## 100-case full v0

远端环境：

- host: `lenovo@10.147.18.151`
- models: `qwen2.5:7b`, `llama3.2:latest`
- each run: first 100 cases, `policy_only`, `top_k=0`
- conditions: `abstract`, `boundary`, `action_rubric_v2`

Text-free summary:

- `pilot/results/dynabench_policy_gap_v0_action_rubric_v2_100case_summary.json`

### 关键结果

qwen2.5:7b：

- abstract exact adherence: 0.4200; family adherence: 0.5600
- boundary exact adherence: 0.3800; family adherence: 0.7800
- action_rubric_v2 exact/family adherence: 0.7900
- boundary family delta vs abstract: +0.2200
- action_rubric_v2 exact delta vs abstract: +0.3700
- action_rubric_v2 exact delta vs boundary: +0.4100

llama3.2：

- abstract exact adherence: 0.6300; family adherence: 0.6400
- boundary exact adherence: 0.4400; family adherence: 0.7700
- action_rubric_v2 exact adherence: 0.6800; family adherence: 0.7000
- boundary family delta vs abstract: +0.1300
- action_rubric_v2 exact delta vs abstract: +0.0500
- action_rubric_v2 exact delta vs boundary: +0.2400

### 解释

100-case 结果比 30-case 更能支持我们当前的方法假设：

- `boundary` 主要解决的是边界理解问题，所以它在两个模型上都提升了 decision-family adherence：qwen 从 0.5600 到 0.7800，llama 从 0.6400 到 0.7700。
- 单独给出 boundary 仍然不能保证 exact action 对齐，因为模型会输出 `contextualize`、`restrict` 等非目标动作；这正是 policy-to-operation gap 的操作层表现。
- `action_rubric_v2` 把 policy boundary 绑定到 `allow/remove` 动作空间后，显著提高 exact-action adherence：qwen 从 abstract 的 0.4200 到 0.7900，llama 从 boundary 的 0.4400 到 0.6800。
- llama 上 action rubric 的 family adherence 相比 boundary 从 0.7700 降到 0.7000，但 exact adherence 从 0.4400 升到 0.6800。这说明 action rubric 的作用不是单纯提高粗粒度 family 判断，而是把模型从开放式审核建议拉回闭集操作动作。对论文表述来说，boundary clarification 和 action rubric 应分别服务于不同误差层级。

### 当前判断

这轮 100-case 不是为了证明我们能刷高 DynaBench 分数，而是为了验证一个机制链条：

1. abstract policy 会触发模型默认审核偏置；
2. boundary clarification 能改善 policy boundary 的粗粒度理解；
3. action rubric 能把已理解的 boundary 进一步投影到目标动作空间，降低 exact-action error。

因此，当前方向可以继续推进，但下一步不应立刻做更大模型堆叠。更关键的是把方法从人工写 rubric 推进为可复现的 policy compiler / gap diagnostic：输入自然语言 policy，自动发现缺失的 boundary 与 action binding，并输出可审计的 clarified policy。
