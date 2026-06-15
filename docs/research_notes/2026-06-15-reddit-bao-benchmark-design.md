# 2026-06-15 Reddit-BAO Benchmark 与方法路线设计

## 0. 本文目的

这份文档固定下一阶段研究路线，避免继续围绕 12 条自构造 smoke cases 反复调方法。

核心决定：

> 先以公开 Reddit moderation 数据集建立可复现的 policy-to-operation benchmark，确认高层 public rules 到真实 moderator decision 之间的痛点，再在小规模 BAO overlay 上设计 POLAR / compiler 方法；暂不直接上 agent RL、LoRA 或大规模训练。

本文记录：

1. 为什么选择 Reddit 作为主数据基座；
2. BARRED 数据/任务如何作为辅助 benchmark，而不是主线替代；
3. 如何避免信息泄露；
4. 如何体现我们的“数据优化”和“方法优化”；
5. 什么实验结果才说明这条路值得继续；
6. 什么时候才升级到 agent / RL / LoRA compiler。

## 1. 当前问题重新表述

我们原来的 pilot 已经说明一个局部现象：

- `boundary clarification` 主要降低 decision-family error；
- `action rubric` 进一步降低 exact-action error；
- 普通 rewrite baseline 很难替代 boundary/action 结构。

但这些结果来自自构造 small probes。继续只靠小 smoke 会产生两个问题：

1. 方法容易调到局部最优，只会修当前 12 条 case；
2. 审稿人可能质疑：这是不是一个人工构造的 prompt engineering 现象，而不是公开审核任务中的一般问题。

因此下一阶段要先固定公开数据基座。我们要证明的不是“我们的 prompt 对 12 条 case 有效”，而是：

> Publicly stated moderation rules are incomplete operational specifications. Given public rules and observed moderation outcomes, models need a boundary/action operationalization layer to better execute the intended moderation behavior.

## 2. 数据源定位

### 2.1 Reddit moderation dataset：主数据基座

我们优先使用 **Multilingual Content Moderation: A Case Study on Reddit** 相关数据。

该数据适合主线，因为它提供：

```text
input case          = Reddit comment
regime/domain       = subreddit
public policy text  = subreddit rules / description / metadata
observed decision   = kept / removed by moderator
```

需要严格区分：

- `1.8M comments` 是待审核输入，不是 policy；
- `56 subreddits` 是 regime / domain，不是 policy；
- `subreddit rules + description` 才是我们可以使用的 publicly stated moderation policy；
- `kept / removed` 是真实 moderator decision，但不是 exact action taxonomy。

因此 Reddit 原始数据不是一个完美的 policy benchmark。它的价值在于：公开规则确实存在，但它们通常不足以解释所有真实审核执行。这正好对应我们的 `policy-to-operation gap`。

我们不能 claim：

> 我们恢复了 Reddit 真实内部审核 policy。

我们可以 claim：

> We study the gap between publicly stated community rules and observed moderation decisions.

### 2.2 BARRED：policy-native 辅助 benchmark

BARRED 的输入输出形式更接近 custom guardrail：

```text
natural-language policy / rule
+ input
-> violation / non-violation label
```

这非常适合作为辅助基准，因为它天生包含 policy rule。但 BARRED 本身是一篇方法论文的数据和评测体系，如果我们完全围绕它做，论文容易被读成：

> 在 BARRED benchmark 上做了一个新的 prompt/compiler baseline。

因此本文建议：

- Reddit 是主 benchmark；
- BARRED 是 policy-native sanity check 和强相关 baseline；
- 不攻击 BARRED，不 claim BARRED 错；
- 用 BARRED 回答：当 policy 明确给出时，我们的 compiler 是否仍有价值；
- 用 Reddit 回答：公开规则到真实审核执行之间是否存在现实 gap。

### 2.3 DSA Transparency Database：action taxonomy 参考

DSA Transparency Database 有真实平台 moderation actions 和 restriction categories，但通常不提供完整待审核原文，因此不适合作为主 text-to-decision benchmark。

它适合作为：

- action space 校准；
- exact-action taxonomy 的现实参考；
- 论文 related work / motivation 中的真实平台操作空间证据。

### 2.4 Toxicity / safety 数据集：外部验证，不做主 claim

Civil Comments、ToxicChat、OpenAI moderation release、HateCheck、BeaverTails 等可以作为外部泛化或 sanity check。

但它们通常只有 toxicity / harm category / safety label，没有 public policy text，因此不能作为 policy-to-operation 主实验。

## 3. 我们对 Reddit 的“优化”是什么

Reddit 原始数据是：

```text
comment + subreddit + public rules -> kept / removed
```

我们的贡献不是改动原始 label，也不是重新训练一个普通 classifier，而是在公开审核数据上增加一个 **Boundary-Action Overlay (BAO)**：

```text
Raw Reddit moderation data
-> policy provenance normalization
-> candidate rule mapping
-> boundary variable extraction
-> contrast pair construction
-> operational policy compilation
```

### 3.1 BAO overlay 字段

建议的 overlay schema：

```json
{
  "source_dataset": "reddit_moderation",
  "case_id": "...",
  "subreddit": "...",
  "comment": "...",
  "public_policy": {
    "rules": ["..."],
    "description": "...",
    "provenance": "subreddit_public_rules"
  },
  "observed_decision": "kept_or_removed",
  "candidate_rule": "...",
  "decision_family": "non_intervention_or_intervention",
  "boundary_variables": [
    "quotation",
    "endorsement",
    "targeted_attack",
    "slur_reclaimed_or_directed",
    "medical_advice",
    "self_promotion",
    "off_topic",
    "spam_pattern"
  ],
  "minimal_contrast": {
    "paired_case_id": "...",
    "changed_variable": "..."
  },
  "rationale": "..."
}
```

第一阶段不强求 exact action，因为 Reddit 原始标签只有 kept / removed。exact action 可以在 BAO 子集里作为拓展层：

```text
allow / contextualize / remove / escalate
```

但主任务先保持二分类：

```text
kept vs removed
```

这样不会把原数据没有的动作空间硬塞进去。

### 3.2 数据优化的实质

数据优化不是“做更多标注”本身，而是把普通 label 数据变成可研究 policy-to-operation 的结构数据：

| 原始 Reddit 字段 | BAO 增强 |
|---|---|
| comment | comment + optional context |
| subreddit | regime id |
| rules / description | normalized public policy card |
| kept / removed | observed decision family |
| 无 violated rule | candidate rule mapping |
| 无边界变量 | boundary variables |
| 无解释 | policy-grounded rationale |
| 无 matched probes | contrast pairs |

如果这个 overlay 能让模型更稳定地执行 public rules，那就是我们的数据贡献。

## 4. 信息泄露与 split 设计

你提出的“信息泄露”担心是对的。我们必须明确：方法可以看 train/dev，但不能看 test。

### 4.1 合法使用

合法：

```text
train rules + train comments + train labels
-> induce operational policy
-> evaluate on held-out comments / held-out subreddits
```

这属于正常监督或弱监督方法。

### 4.2 不合法使用

不合法：

```text
look at test labels / test mistakes
-> manually add cues
-> evaluate on the same test cases
```

这会把方法调成 test-specific patch。

### 4.3 必做 split

至少做两个 split：

| split | 目的 |
|---|---|
| in-subreddit split | 同一 subreddit 内，public rules + train examples 能否改善 held-out comments |
| cross-subreddit split | 面对新 subreddit / 新 public rules，方法是否仍能迁移 |

如果时间允许，再做 time-based split：

| split | 目的 |
|---|---|
| time split | 模拟审核规则与执行习惯随时间变化，避免随机 split 过于乐观 |

### 4.4 三个数据层

建议固定三个层级：

1. `Raw-Reddit-Full`：原始大数据，只做统计、采样和基础评测；
2. `Reddit-Benchmark-Core`：固定若干 subreddit 的 train/dev/test；
3. `BAO-Reddit-Overlay`：小规模人工/半自动增强子集，用于方法开发和解释性评测。

## 5. 第一阶段：先确认 Reddit 上的痛点

第一阶段不做复杂方法，只建立上下界。

### 5.1 输入条件

| 条件 | 输入给模型 |
|---|---|
| comment-only | comment |
| raw-rules | comment + subreddit public rules |
| rules+description | comment + rules + subreddit description |
| ordinary-rewrite | comment + LLM rewritten rules |
| length-matched rewrite | comment + 与 POLAR 长度接近的普通 rewrite |
| few-shot examples | comment + public rules + few moderated examples |
| retrieval examples | comment + public rules + retrieved similar examples |
| supervised classifier | train labels only, 不显式建模 policy |
| oracle-ish rule mapping | comment + public rules + candidate rule |

### 5.2 要看的指标

基础指标：

- accuracy；
- macro F1；
- removed-class precision / recall；
- calibration；
- per-subreddit performance；
- cross-subreddit generalization。

policy-grounded 指标：

- rationale 是否引用 public rules；
- 预测错误是否集中在 rules ambiguous 的 case；
- raw rules 是否真的比 comment-only 有帮助；
- few-shot / retrieval 是否只是记住 community style，而不是理解 rules。

### 5.3 痛点成立标准

满足以下任意两条，就说明值得继续：

1. `raw-rules` 明显优于 `comment-only`，但仍有大量错误；
2. `ordinary-rewrite` 和 `length-matched rewrite` 提升有限；
3. 不同大模型在同一规则下决策不稳定；
4. 错误集中在可解释的 boundary variables；
5. few-shot / retrieval 提升了分数，但 rationale 不稳定或跨 subreddit 迁移弱。

如果强模型 + raw rules 已经接近饱和，则要缩小问题：只研究 hard subsets / boundary cases，而不是全量分类。

## 6. 第二阶段：BAO 小规模方法

只有第一阶段确认痛点后，才进入 BAO 方法。

### 6.1 BAO 子集构造

建议起步规模：

```text
5-10 subreddits
每个 subreddit 200-500 条样本
其中 50-100 条做 BAO overlay
```

优先选择规则类型差异大的 subreddit，例如：

- 严格科学/医学讨论；
- 财务建议；
- 健身/健康建议；
- 政治讨论；
- meme / satire / casual community；
- self-promotion / spam 边界明显的社区。

### 6.2 轻量 POLAR compiler v1

先不要上 RL。v1 应该是可解释、可控、可 debug 的：

```text
public rules
+ train examples
+ BAO overlay
-> candidate rule clusters
-> boundary variable table
-> conflict priority table
-> compact operational policy card
```

输出不是训练数据，而是：

```text
P+ = compiled operational policy
sidecar = evidence / rule mapping / boundary variables / contrast pairs
```

部署时只给模型 `P+`；sidecar 用于论文分析和复现。

### 6.3 与 baseline 的核心差异

| 方法 | 本质 |
|---|---|
| ordinary rewrite | 改写 wording |
| few-shot | 给历史例子 |
| retrieval | 给相似例子 |
| classifier | 直接拟合 label |
| BARRED-like | 生成 synthetic labeled cases |
| POLAR / BAO compiler | 归纳 boundary/action variables，并编译 policy |

我们要证明：

> 不是更多文字、更多例子或更多标签本身起作用，而是 boundary/action 结构使 public rules 更可执行。

## 7. 第三阶段：什么时候上 agent / RL / LoRA

现在不建议直接做 agent RL 或 LoRA compiler。

原因：

1. benchmark 未冻结，reward 不清楚；
2. 如果不知道错误来自 policy gap、数据偏差还是模型能力，上 RL 会把问题混在一起；
3. 复杂方法容易过拟合 dev set；
4. 论文会变成工程-heavy，但核心科学问题不一定更清楚。

### 7.1 升级条件

只有满足以下条件，才上复杂方法：

1. Reddit benchmark 上 raw rules / rewrite / few-shot 的上界明确；
2. BAO compiler v1 在 held-out split 上稳定优于普通 rewrite；
3. 错误分析显示主要瓶颈是 cue selection / compression / conflict handling；
4. 评估协议已经冻结，不能边看 test 边改方法。

### 7.2 可选复杂方法

之后可以考虑三种：

| 方法 | 输入 | 输出 | 风险 |
|---|---|---|---|
| agentic compiler | public rules + train examples + BAO | P+ and sidecar | 成本高，难复现 |
| LoRA compiler | rules + examples | operational policy card | 需要训练集和格式稳定 |
| RL compiler | compiler outputs with reward | optimized P+ | reward 设计困难，易过拟合 |

优先级建议：

```text
deterministic BAO compiler
-> agentic compiler
-> LoRA compiler
-> RL compiler
```

RL 放最后，不作为当前论文的必要条件。

## 8. 与 BARRED 的关系

BARRED 不应该被当作对手攻击，而应该被放入更稳的位置：

1. BARRED 代表 data-first / synthetic guardrail training；
2. 我们代表 policy operationalization / boundary-action overlay；
3. 两者可以互补；
4. 我们可以测试：在 BARRED policy-native setting 下，POLAR 是否也能改善 raw-policy prompting；
5. 我们也可以测试：BAO preflight 是否能提高 synthetic data 的 sample yield 或降低 pseudo-consensus。

建议实验角色：

| BARRED 用法 | 目的 |
|---|---|
| 直接跑 BARRED test set | policy-native sanity check |
| BARRED-like synthetic baseline | 证明 data-first 不是唯一方案 |
| BARRED + BAO preflight | 证明 BAO 可以作为 synthetic pipeline 的前置诊断 |

不能 claim：

- BARRED 错；
- synthetic data 没用；
- 不训练就一定优于 BARRED fine-tuning。

可以 claim：

> Synthetic labeled data and operational policy compilation address different parts of custom moderation. BAO tests whether the policy text is operationally sufficient before labels are generated or consumed.

## 9. 论文路线更新

推荐论文主线：

> Existing moderation datasets provide labels but often lack the operational policy structure that explains why a rule applies. We construct a Boundary-Action Overlay over public Reddit moderation data and show that compiling public rules into operational policies improves LLM moderation over raw rules, ordinary rewrites, and example-based prompting.

对应贡献：

1. 提出 public-rules-to-operation gap；
2. 构建 BAO-Reddit benchmark：公开规则、真实审核标签、boundary/action overlay；
3. 提出 POLAR compiler：把 public rules + small overlay 编译成 operational policy；
4. 系统比较 raw rules、rewrite、few-shot、retrieval、data-only classifier、BARRED-like baseline；
5. 证明该方法跨模型、跨 subreddit 或 hard boundary subset 有稳定收益。

## 10. 第一阶段执行计划

### Step A：数据可用性确认

确认 Reddit 数据下载方式、字段、license/terms、是否含 subreddit rules。

输出：

```text
docs/research_notes/YYYY-MM-DD-reddit-dataset-audit.md
```

### Step B：抽样和字段规范

建立 `Reddit-Benchmark-Core` 的字段规范：

```text
case_id
subreddit
comment
parent_or_thread_context optional
public_rules
description
label kept/removed
split
```

### Step C：baseline 上下界

先用少量模型：

- qwen2.5:7b；
- llama3.2；
- 一个闭源强模型，如果成本允许。

先跑：

- comment-only；
- raw-rules；
- rules+description；
- ordinary rewrite；
- few-shot。

### Step D：痛点判断

写结果 memo，决定是否进入 BAO overlay。

进入条件：

- raw-rules 有帮助但不够；
- rewrite 不能解决；
- hard boundary cases 明显；
- 规则相关 rationale 不稳定。

## 11. 当前决策

当前不直接做：

- agent RL；
- LoRA compiler；
- 大规模 fine-tuning；
- 全量 1.8M comments 实验；
- exact-action 全量标注。

当前先做：

```text
Reddit benchmark design
-> 数据字段审计
-> 小规模 baseline 上下界
-> BAO overlay 子集
-> deterministic / lightweight POLAR compiler
```

这条路线的优势是：

1. 先固定公开数据和评测协议，减少 local minimum；
2. 先确认 pain，再决定方法复杂度；
3. 让 Reddit 负责现实性，BARRED 负责 policy-native 对照；
4. 保留后续上 agent/RL/LoRA 的空间，但不让复杂方法绑架论文主线。

## 12. 参考资料

- Multilingual Content Moderation: A Case Study on Reddit: https://aclanthology.org/2023.eacl-main.276/
- Reddit moderation paper PDF: https://aclanthology.org/2023.eacl-main.276.pdf
- BARRED GitHub: https://github.com/plurai-ai/BARRED
- BARRED paper: https://arxiv.org/abs/2604.25203
- BARRED dataset: https://huggingface.co/datasets/Plurai/BARRED
- DSA Transparency Database: https://transparency.dsa.ec.europa.eu/

