# Reddit PullPush Resolver Smoke 运行记录

日期：2026-06-16

## 背景

Reddit 官方 API app 创建目前被新的 API 注册/审批流程卡住，`api/info.json?id=t1_<comment_id>` 在当前环境返回 `403 Blocked`。

为了判断 Reddit 数据路线是否仍然可行，我们实现了一个 **PullPush pilot fallback resolver**。它的用途是把已有公开 comment id 转成可本地实验的 raw text，先验证覆盖率和数据质量。

重要边界：

- PullPush 是第三方 archive，只作为 pilot/coverage test fallback；
- 论文最终版本仍应优先争取 Reddit 官方 API access 或原数据集作者 DUA；
- hydrated 正文只写入 `data/raw/`，该目录被 `.gitignore` 忽略；
- 提交到 Git 的 summary 不包含正文。

## 新增代码

```text
pilot/src/regime_pilot/reddit_pullpush_resolver.py
tests/test_reddit_pullpush_resolver.py
```

核心行为：

- 输入：`pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl`
- 输出 raw：`data/raw/*.jsonl`
- 输出 summary：`pilot/results/*.json`
- 每条 hydrated raw record 保留：
  - `text`
  - `body_sha256`
  - `retrieval_source=pullpush`
  - `retrieved_at`
  - `text_status`
  - `subreddit_match`
- summary 只保留 count，不保留正文。

## Smoke 1：前 100 条

命令：

```powershell
$env:PYTHONPATH='pilot/src'

& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m regime_pilot.reddit_pullpush_resolver `
  --queue pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl `
  --output data/raw/reddit_bao_pullpush_smoke100.jsonl `
  --summary pilot/results/reddit_bao_pullpush_smoke100_summary.json `
  --limit 100 `
  --sleep-seconds 0.3 `
  --max-retries 2 `
  --retry-sleep-seconds 3
```

结果：

| metric | value |
|---|---:|
| records | 100 |
| hydrated | 90 |
| hydrated rate | 90.0% |
| unavailable | 7 |
| error | 3 |

该 smoke 只覆盖 `science`，因为原始 queue 按 subreddit 排序，前 100 条都来自 `science`。

## Smoke 2：balanced 120

为避免只看 `science`，额外生成了一个无正文 smoke queue：

```text
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_smoke120.jsonl
```

每个 subreddit 20 条：

```text
science, news, worldnews, space, futurology, nfl
```

命令：

```powershell
$env:PYTHONPATH='pilot/src'

& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m regime_pilot.reddit_pullpush_resolver `
  --queue pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_smoke120.jsonl `
  --output data/raw/reddit_bao_pullpush_balanced_smoke120.jsonl `
  --summary pilot/results/reddit_bao_pullpush_balanced_smoke120_summary.json `
  --sleep-seconds 0.3 `
  --max-retries 2 `
  --retry-sleep-seconds 3
```

结果：

| metric | value |
|---|---:|
| records | 120 |
| hydrated | 103 |
| hydrated rate | 85.83% |
| unavailable | 13 |
| error | 4 |

按 subreddit：

| subreddit | hydrated | unavailable | error |
|---|---:|---:|---:|
| futurology | 16 | 4 | 0 |
| news | 19 | 1 | 0 |
| nfl | 17 | 2 | 1 |
| science | 16 | 4 | 0 |
| space | 18 | 0 | 2 |
| worldnews | 17 | 2 | 1 |

## 初步判断

PullPush fallback 能拿到相当比例的正文：

- 单 subreddit smoke：90.0%
- balanced smoke：85.83%

这说明 Reddit 路线没有死。我们已经可以先构造一个 100-500 条规模的 `Reddit-Text-Core` pilot，用来跑第一版模型 benchmark。

当前主要问题是：

1. `429` 限流仍存在，resolver 已加入 retry/backoff，但全量 4,800 条需要更慢的节奏；
2. 一部分 comment 已删除或不可用，属于不可恢复缺口；
3. PullPush 是第三方来源，最终论文需要谨慎表述，最好同时保留官方 API/DUA 申请路线。

## 下一步建议

短期：

1. 用 balanced queue 跑 500 条，目标是获得至少 400 条 hydrated text；
2. 从 hydrated records 构造 `Reddit-Text-Core`；
3. 跑 comment-only / policy-card 条件的小矩阵；
4. 如果信号存在，再扩到 1,000-2,000 条。

中期：

1. 继续申请 Reddit API access 或原数据集作者 full-text DUA；
2. 把 PullPush 来源标注为 pilot fallback；
3. 在论文实验章节明确报告 text reconstruction coverage 和 missingness。
