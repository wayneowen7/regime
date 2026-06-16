# Reddit PullPush Collection 运行记录

日期：2026-06-16

## 目标

开始从 Reddit comment id 采集正文，并确保正文与我们已有的 `id / label / expected_decision / policy_card_id` 一一对应。

本轮不追求全量完美采集，先获得可用于 `Reddit-Text-Core` pilot 的本地样本。

## 输入

基础队列：

```text
pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl
```

每条队列记录已经包含：

```text
case_id
comment_id
reddit_fullname
subreddit
split
label
expected_decision
policy_card_id
```

因此 resolver 返回正文时，会直接写在同一条记录的 `text` 字段中，不会丢失 label 对应关系。

## 采集策略

全量 4,800 条直接跑会很慢，而且当前 resolver 是批处理写出；一次长任务超时会丢失该批进度。

因此本轮改为 chunked collection：

- 构造 balanced 600 queue；
- 每个 chunk 120 条；
- 6 个 subreddit 各 20 条；
- 每个 chunk 单独输出 raw 和 summary。

生成的队列：

```text
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_600.jsonl
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_600_chunk1.jsonl
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_600_chunk2.jsonl
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_600_chunk3.jsonl
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_600_chunk4.jsonl
pilot/data/reddit_bao/reddit_bao_hydration_queue_balanced_600_chunk5.jsonl
```

其中 chunk 1 复用了之前的 balanced smoke 120 raw 结果。

## 已完成采集

已完成：

```text
chunk1: data/raw/reddit_bao_pullpush_balanced_smoke120.jsonl
chunk2: data/raw/reddit_bao_pullpush_balanced_600_chunk2.jsonl
chunk3: data/raw/reddit_bao_pullpush_balanced_600_chunk3.jsonl
```

合并输出：

```text
data/raw/reddit_bao_pullpush_balanced_360.jsonl
data/raw/reddit_bao_text_core_pullpush_balanced_360.jsonl
```

注意：`data/raw/` 被 `.gitignore` 忽略，正文不会进入 Git。

提交到 Git 的无正文 summary：

```text
pilot/results/reddit_bao_pullpush_balanced_360_summary.json
```

## 结果

合并 chunk 1-3：

| metric | value |
|---|---:|
| attempted records | 360 |
| hydrated records | 298 |
| hydrated rate | 82.78% |
| unavailable | 19 |
| error | 43 |

按 subreddit：

| subreddit | attempted | hydrated | unavailable | error |
|---|---:|---:|---:|---:|
| futurology | 60 | 53 | 4 | 3 |
| news | 60 | 53 | 3 | 4 |
| nfl | 60 | 41 | 2 | 17 |
| science | 60 | 45 | 4 | 11 |
| space | 60 | 54 | 2 | 4 |
| worldnews | 60 | 52 | 4 | 4 |

## Label 对应关系校验

已对 hydrated-only Text-Core 做字段校验：

```text
data/raw/reddit_bao_text_core_pullpush_balanced_360.jsonl
```

结果：

```json
{
  "count": 298,
  "missing_or_bad": [],
  "all_ok": true
}
```

每条 hydrated record 都包含：

```text
case_id
comment_id
reddit_fullname
subreddit
split
label
expected_decision
policy_card_id
text
body_sha256
retrieval_source
retrieved_at
```

这满足“爬取下来的 comment 内容和已有 id、label 对应起来”的要求。

## Retry 情况

从 360 条中抽出 43 条 `text_status=error` 构造 retry queue：

```text
pilot/data/reddit_bao/reddit_bao_pullpush_balanced_360_retry_errors.jsonl
```

已尝试慢速 retry：

```powershell
--sleep-seconds 0.5
--max-retries 5
--retry-sleep-seconds 8
```

但该批在 15 分钟内仍未完成并超时，没有写出 retry raw/summary。初步判断 PullPush 对这些 ID 的限流比较持续。

下一步如果继续 retry，应先把 resolver 改成 streaming/resume 写出，避免长 retry 批次再次丢进度。

## 当前判断

Reddit 数据路线可以继续。

我们已经有 298 条可用的 hydrated comment text，覆盖 6 个 subreddit，且每条都与 label / policy card 保持对应。这足够做第一版小型 `Reddit-Text-Core` benchmark。

下一步建议：

1. 用这 298 条先跑 comment-only 和 policy-card 条件；
2. 同时把 resolver 改成 streaming/resume；
3. 再采 chunk 4-5 或重试 error queue；
4. 等 benchmark 信号明确后，再决定是否全量 4,800 条。
