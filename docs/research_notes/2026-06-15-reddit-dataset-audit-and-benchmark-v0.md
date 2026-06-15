# 2026-06-15 Reddit 数据集审计与 Benchmark v0 设计

## 0. 当前结论

本轮已经下载并审计了 Reddit multilingual content moderation 的公开仓库：

```text
.local_data/multilingual_content_mod
```

该目录已加入 `.gitignore`，不会被提交到 GitHub。

最重要的结论：

1. 公开仓库只提供 `comment id`，不提供评论正文；
2. `.pkl` 数据字段只有 `label / id / subreddit`；
3. `rules/2022-06-27/` 下提供 56 个 subreddit 的 public metadata，包括 description、structured subreddit rules、site rules；
4. 公开数据足够做 policy/rules 审计和 benchmark 结构设计；
5. 若要跑 LLM moderation benchmark，必须先获取 comment text：
   - 走作者 data request form；
   - 或用 PRAW/Reddit API hydrate comment ids；
   - 或寻找合规的历史 Reddit/Pushshift 备选源。

因此，下一步不能直接跑模型大矩阵。必须先完成 **Text Acquisition Gate**。

## 1. 数据源与下载方式

公开仓库：

- GitHub: https://github.com/mye1225/multilingual_content_mod

本地下载方式：

```powershell
git clone ssh://git@ssh.github.com:443/mye1225/multilingual_content_mod.git .local_data\multilingual_content_mod
```

README 明确说明：

- 为遵守 Reddit policy，公开仓库只释放 comment ids；
- 用户可用 PRAW retrieve comment text；
- 若需要作者原始 text content dataset，需要填写 data request form 并同意 DUA。

这意味着公开 repo 不足以直接构建：

```text
comment text + public rules -> kept / removed
```

但它足以确认：

```text
comment id + subreddit + label
subreddit public rules / metadata
```

## 2. `.pkl` 文件格式

对公开 `.pkl` 文件审计后，确认它们是 pandas DataFrame。

代表文件：

```text
balanced/data-en/train.pkl
```

字段：

| column | dtype | 含义 |
|---|---|---|
| `label` | int64 | 二分类标签，推定 `0=kept`, `1=removed` |
| `id` | object | Reddit comment id，不含 `t1_` 前缀 |
| `subreddit` | object | subreddit 名称 |

样例：

| label | id | subreddit |
|---:|---|---|
| 0 | i6hvw1p | worldnews |
| 1 | hycl8oq | news |
| 0 | i7vfplp | grandpajoehate |

注意：

- 文件中没有评论正文；
- 文件中没有 parent/thread context；
- 文件中没有 violated rule；
- 文件中没有 rationale；
- 文件中没有 exact moderation action。

## 3. 数据 split 与规模

公开仓库包含两个 family：

```text
original/
balanced/
```

以及多种语言目录：

```text
data-en
data-de
data-es
data-fr
data-mllm
```

### 3.1 English balanced split

推荐第一阶段优先使用：

```text
balanced/data-en
```

原因：

- 类别更平衡，适合 LLM benchmark；
- 仍覆盖大量 subreddit；
- 能减少 original split 中 removed class 极端稀疏带来的指标不稳定。

审计统计：

| file | rows | subreddits | label 0 | label 1 | label 1 rate |
|---|---:|---:|---:|---:|---:|
| `train.pkl` | 1,016,386 | 49 | 528,846 | 487,540 | 0.4797 |
| `val.pkl` | 56,460 | 48 | 29,379 | 27,081 | 0.4796 |
| `test-en.pkl` | 56,466 | 49 | 29,307 | 27,159 | 0.4810 |

### 3.2 English original split

原始分布更贴近真实线上审核，但 removed class 极度稀疏。

| file | rows | subreddits | label 0 | label 1 | label 1 rate |
|---|---:|---:|---:|---:|---:|
| `train.pkl` | 1,333,592 | 48 | 1,308,545 | 25,047 | 0.0188 |
| `val.pkl` | 74,067 | 48 | 72,701 | 1,366 | 0.0184 |
| `test-en.pkl` | 74,101 | 48 | 72,716 | 1,385 | 0.0187 |

建议：

- `balanced` 用于模型能力比较；
- `original` 用于现实分布评估和 calibration；
- 不要只报 accuracy，否则 original split 上多数类 baseline 会虚高。

## 4. Subreddit rules metadata 审计

规则目录：

```text
rules/2022-06-27/<subreddit>/subreddit_metadata.json
```

审计结果：

| 项目 | 数值 |
|---|---:|
| metadata subreddits | 56 |
| total structured rules | 478 |
| structured comment rules | 23 |
| structured link rules | 159 |
| subreddits with at least one rule | 52 |
| subreddits with at least one `kind=comment` rule | 12 |

这暴露了一个重要限制：

> 数据本身是 comment moderation，但 structured rules 中只有 12 个 subreddit 明确提供 `kind=comment` 规则。许多 community 的评论规范可能写在 description 中，或者没有用 structured comment rule 表达。

因此 benchmark 不能简单把所有 `rules.rules` 都当成 comment policy。必须做 policy provenance 分层。

## 5. Subreddit 覆盖关系

`balanced/data-en` 覆盖 49 个 subreddit。

规则目录覆盖 56 个 subreddit。

差异：

- data 中有但 rules 目录没有：`catsstandingup`
- rules 中有但 English data 中没有：`argaming`, `argentina`, `de`, `finanzen`, `ich_iel`, `moi_dlvv`, `quebec`, `rance`

因此第一版 benchmark 应排除：

```text
catsstandingup
```

除非后续能补齐 public rules。

## 6. 适合第一阶段主攻的 subreddit

优先选择具有 explicit comment rules 且样本量足够的 subreddit。

| subreddit | comment rules | balanced-en rows | removed label 1 | 规则特点 |
|---|---:|---:|---:|---|
| `science` | 6 | 224,976 | 112,476 | off-topic, abuse, anecdote, evidence, medical advice |
| `news` | 4 | 146,531 | 73,266 | racism/sexism, rudeness, jokes/memes, celebrating death |
| `worldnews` | 3 | 114,061 | 57,029 | bigotry, personal attacks, memes/NSFW |
| `space` | 2 | 28,352 | 14,175 | low-effort/meme/joke/troll, anti-scientific comments |
| `futurology` | 1 | 44,687 | 22,333 | comment quality |
| `coronavirus` | 1 | 50,708 | 25,350 | bots / civility-adjacent policy |
| `covid19` | 1 | 5,126 | 2,563 | be civil |
| `nfl` | 1 | 14,237 | 7,133 | personal attack / slur |
| `feminism` | 1 | 4,877 | 2,437 | derailing prohibited |
| `anime` | 1 | 11,602 | 5,801 | source-material comment boundary |

第一阶段建议从 6 个开始：

```text
science, news, worldnews, space, futurology, nfl
```

理由：

- 英文社区；
- comment rules 明确；
- 样本量足够；
- 规则类型多样；
- 适合观察 public-rules-to-operation gap。

第二批可加入：

```text
coronavirus, covid19, feminism, anime
```

## 7. Policy card 设计

每个 subreddit 构造一个 public policy card。

### 7.1 P0：structured comment rules

优先使用：

```json
{
  "kind": "comment",
  "short_name": "...",
  "description": "...",
  "violation_reason": "...",
  "priority": 0
}
```

P0 是第一阶段主实验的 policy 来源。

### 7.2 P1：description-extracted comment policy

当 structured comment rules 不完整时，从 `description` 中抽取 comment rules。

例如 `science` description 明确包含：

```text
Comment Rules
1. No off-topic comments, memes, low-effort comments or jokes
2. No abusive or offensive comments
...
```

P1 需要额外抽取步骤，不能和 P0 混为一谈。

### 7.3 P2：site rules

Reddit site rules 可作为通用安全 policy，例如 spam、personal/confidential information、threatening/harassing/inciting violence。

P2 可用于补充，但不能替代 subreddit-specific policy。

### 7.4 P3：link/submission rules

由于当前 task 是 comment moderation，`kind=link` 规则不应默认进入 comment policy。

除非：

- comment 明显讨论 submission/title/source；
- 或后续有 submission context；
- 或作为 ablation 测试 “wrong policy context” 的干扰影响。

## 8. Text Acquisition Gate

没有 comment text 就不能做 LLM moderation benchmark。

### 8.1 匿名 Reddit API 测试

本轮测试：

```text
https://www.reddit.com/api/info.json?id=t1_i6hvw1p
https://www.reddit.com/api/info.json?id=t1_hycl8oq
```

结果：

```text
403 Forbidden
```

说明匿名 API 当前不可用，至少本机当前环境无法直接 hydrate。

### 8.2 三条可行路径

| 路径 | 优点 | 风险 |
|---|---|---|
| 作者 data request | 最完整，合规，最适合论文 | 需要等待审批，可能有 DUA 限制 |
| PRAW + Reddit API credentials | 可控，可复现 hydrate ids | 需要 API credentials，可能有 rate limit / deleted comments |
| 历史 Reddit dump / Pushshift | 可能批量恢复旧评论 | 可用性和合规性不稳定 |

建议优先级：

1. 先提交作者 data request；
2. 同时准备 PRAW hydration script；
3. 如果 API 成本/限制太高，再评估 Pushshift 或其他历史 dump。

## 9. Benchmark v0 设计

### 9.1 Benchmark 名称

暂定：

```text
Reddit-BAO-Core
```

### 9.2 数据层级

| 层级 | 内容 | 用途 |
|---|---|---|
| `Reddit-ID-Core` | id, subreddit, label, split, policy card | 当前可构造 |
| `Reddit-Text-Core` | text, subreddit, label, split, policy card | text acquisition 后构造 |
| `BAO-Reddit-Overlay` | candidate rule, boundary variables, rationale, contrast pairs | 小规模方法开发 |

当前只能稳定构造 `Reddit-ID-Core`。

### 9.3 第一版 Core subset

建议：

```text
subreddits = science, news, worldnews, space, futurology, nfl
source = balanced/data-en
split = existing train/val/test-en
per-subreddit sample = 500 train + 100 val + 200 test
class balance = preserve balanced file's near-balance or stratified 1:1
```

如果拿到 full text，可构建一个小而可控的 LLM benchmark：

```text
6 subreddits * 200 test cases = 1200 test cases
```

这对闭源模型成本相对可控。

### 9.4 Realistic subset

为了避免只在 balanced 数据上得出过于乐观结论，还应构建：

```text
source = original/data-en
subreddits = same 6
sample = preserve realistic removed rate
```

该 subset 主要看：

- removed recall；
- precision；
- calibration；
- class imbalance 下的模型偏置。

## 10. Baseline 矩阵

第一阶段只做上下界，不做复杂 compiler。

| baseline | 输入 | 目的 |
|---|---|---|
| majority baseline | 无文本，只预测多数类 | original split 下 sanity check |
| comment-only LLM | comment | 看模型靠常识/毒性判断的能力 |
| P0-rules LLM | comment + structured comment rules | 测 public rules 是否有帮助 |
| P0+description LLM | comment + rules + description | 测完整 public policy card |
| ordinary rewrite | comment + LLM rewritten policy | 回应“写详细即可” |
| length-matched rewrite | comment + same-length rewritten policy | 控制长度解释 |
| few-shot examples | comment + policy + train examples | 测历史案例能否替代 policy |
| retrieval examples | comment + policy + retrieved examples | 测 data-first / memory route |
| supervised classifier | text -> label | data-only 上界 |

不建议第一阶段做：

- agent RL；
- LoRA compiler；
- full BARRED-like fine-tuning；
- 全量 1.8M 跑闭源模型。

## 11. 第一阶段成功/失败判断

### 11.1 值得继续的信号

满足两条以上即可进入 BAO overlay：

1. `P0-rules` 明显优于 `comment-only`，但仍有明显错误；
2. ordinary rewrite / length-matched rewrite 提升有限；
3. few-shot / retrieval 提升分数但 rationale 不稳定；
4. 模型间对同一 subreddit rules 的决策差异大；
5. 错误集中在可解释的 boundary variables，如 joke vs abuse、critique vs attack、evidence-based claim vs misinformation、personal anecdote vs evidence。

### 11.2 需要调整路线的信号

如果出现以下情况，需要收窄任务：

1. 强模型 + raw rules 已接近饱和；
2. text hydrate 后大量 comments deleted / unavailable，样本质量不足；
3. structured comment rules 覆盖过窄，无法支撑多社区 benchmark；
4. removed label 与 public rules 弱相关，更多反映 moderator style 或不可见上下文。

对应调整：

- 改做 hard subset / boundary subset；
- 转向 P1 description-extracted policies；
- 引入 BARRED policy-native benchmark 做主实验；
- 或把 Reddit 作为现实动机，BARRED 作为主可控实验。

## 12. BAO Overlay 设计

在确认 Reddit benchmark 有痛点后，构造小规模 BAO overlay。

建议字段：

```json
{
  "case_id": "...",
  "subreddit": "science",
  "comment": "...",
  "observed_decision": "removed",
  "policy_card_id": "science_p0_comment_rules",
  "candidate_rule": "No medical advice",
  "boundary_variables": [
    "seeking_advice",
    "offering_specific_treatment",
    "evidence_discussion"
  ],
  "decision_family": "intervention",
  "rationale": "...",
  "contrast_pair_id": "..."
}
```

Overlay 目标不是重标所有数据，而是构建：

- policy-grounded rationale；
- candidate rule mapping；
- boundary variable table；
- minimal contrast pairs；
- compiler sidecar。

## 13. 方法路线更新

第一阶段之后，如果痛点成立，做轻量 POLAR compiler：

```text
public policy card
+ small BAO overlay
-> boundary variable table
-> conflict priority table
-> compact operational policy P+
```

然后比较：

```text
raw rules
ordinary rewrite
few-shot
retrieval
POLAR P+
```

评价：

- kept/removed macro F1；
- removed recall；
- per-subreddit performance；
- rationale-rule match；
- cross-model stability；
- prompt length。

只有当 deterministic / lightweight compiler 稳定有效后，再考虑：

- agentic compiler；
- LoRA compiler；
- RL compiler。

## 14. 与 BARRED 的结合点

BARRED 仍然重要，但位置是辅助：

1. 如果 Reddit text acquisition 卡住，BARRED 可以作为 policy-native fallback；
2. 如果 Reddit 初步结果太 noisy，BARRED 可用来验证 compiler 在明确 policy 下是否有效；
3. 如果我们要回应 synthetic data 路线，BARRED-like baseline 可以比较：
   - data-only fitting；
   - synthetic labels；
   - policy operationalization。

暂不建议把 BARRED 作为主线唯一数据集。

## 15. 下一步任务清单

### Task 1：获取 comment text

优先：

- 提交作者 data request form；
- 准备 Reddit API/PRAW credentials。

### Task 2：构造 `Reddit-ID-Core`

即使没有 text，也可以先构造 id-level manifest：

```text
case_id
comment_id
reddit_fullname = t1_<id>
subreddit
label
split
policy_card_id
```

### Task 3：构造 policy cards

从 rules metadata 生成：

```text
policy_cards/reddit/<subreddit>.json
```

字段：

```text
subreddit
description
p0_structured_comment_rules
p1_description_policy_raw
p2_site_rules
p3_link_rules_excluded_by_default
```

### Task 4：Text-Core 小样本

拿到 text 后，先做：

```text
6 subreddits
balanced data-en
1200 test cases
```

### Task 5：baseline smoke

先跑：

- comment-only；
- P0-rules；
- P0+description；
- ordinary rewrite；
- few-shot。

### Task 6：痛点 memo

写：

```text
docs/research_notes/YYYY-MM-DD-reddit-benchmark-pain-check.md
```

决定是否进入 BAO overlay。

## 16. 当前判断

Reddit 数据集值得继续作为主方向，但要非常清醒：

- 它公开 release 的数据不是完整 text benchmark；
- 它的 structured comment rules 覆盖有限；
- 它适合做 public-rules-to-operation gap；
- 它不适合直接声称“恢复真实审核 policy”；
- 它需要 text acquisition gate；
- 第一阶段应先固定 benchmark 和上下界，再做方法。

最稳路线：

```text
Reddit public repo audit
-> comment text acquisition
-> Reddit-ID-Core / Policy Cards
-> Reddit-Text-Core small benchmark
-> baseline upper/lower bounds
-> BAO overlay subset
-> lightweight POLAR compiler
```

这条路线能把我们的工作从自构造 smoke cases 推向公开、可复现、审核领域相关的数据基座。

## 17. 参考资料

- Multilingual Content Moderation: A Case Study on Reddit: https://aclanthology.org/2023.eacl-main.276/
- Paper PDF: https://aclanthology.org/2023.eacl-main.276.pdf
- Public dataset repository: https://github.com/mye1225/multilingual_content_mod
- PRAW comment API docs: https://praw.readthedocs.io/en/stable/code_overview/models/comment.html

