# Reddit BAO label=1 优先采集记录

## 背景

Reddit BAO 文本恢复的主要瓶颈不是 label=0，而是 label=1/removed 样本。当前全量采集进程仍在运行，但已经观察到大量 label=1 样本返回 `unavailable`，只有极少数 label=1 样本能够恢复出文本。因此，继续直接等待全量队列会让 v0 benchmark 长期受类别失衡影响。

## 当前策略

我们不覆盖已有全量采集结果，而是新增一个 label=1 优先队列：

- 跳过已经 `hydrated` 的 label=1 样本，避免重复消耗请求。
- 纳入尚未处理过的 label=1 样本。
- 纳入此前 `error`、`missing`、`subreddit_mismatch` 的 label=1 样本，用于重试 transient failure。
- 默认不纳入 `unavailable`，因为这类结果通常意味着评论被删除、不可访问或 PushPull 端不可恢复；后续如果需要，可以单独做低频重试队列。

生成的优先队列：

- `pilot/data/reddit_bao/reddit_bao_label1_priority_unseen_error_queue.jsonl`
- `pilot/results/reddit_bao_label1_priority_unseen_error_queue_summary.json`

本轮生成摘要显示：

- source queue: 2400
- selected: 1498
- selected by reason:
  - `not_seen`: 1473
  - `error`: 25
- skipped hydrated: 4
- skipped unavailable: 898

这说明当前数据修复的核心不是继续重复抓已经失败的 terminal unavailable，而是尽快扫完未见过的 label=1 id，并对 transient error 做重试。

## 后台采集

本地新增脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_reddit_label1_priority_background.ps1
```

脚本默认输出到：

- raw stream: `data/raw/reddit_bao_pullpush_label1_priority_stream.jsonl`
- raw summary: `data/raw/reddit_bao_pullpush_label1_priority_stream_summary.json`
- log: `data/raw/logs/reddit_label1_priority_background_*.log`

这些 raw 文件位于 `data/raw/`，不进入 git。后续 benchmark 构建时应合并全量流与 label=1 优先流，并按 `comment_id` 去重，优先保留 `hydrated` 记录。

## 下一步判断

如果 label=1 优先流仍然只有极少数 `hydrated`，则可以形成一个重要结论：仅依赖公开 API/PushPull 从 removed-label benchmark 恢复原文会产生严重可得性偏差。此时论文数据路线需要转向：

1. 只使用可恢复文本子集做小规模机制验证；
2. 补充 X-Guard、BARRED 或其他可公开获得文本的 moderation 数据；
3. 将 Reddit BAO 作为“真实社区规则 + removed label 可得性受限”的外部压力测试，而不是唯一主 benchmark。
