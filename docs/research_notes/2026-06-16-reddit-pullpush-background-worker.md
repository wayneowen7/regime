# Reddit PullPush 后台采集方案

日期：2026-06-16

## 目的

我们已经证明可以通过 PullPush 用 `comment_id` 取回 Reddit comment 正文，并且保持正文和已有的 `case_id / label / expected_decision / policy_card_id` 对齐。

上一轮的问题是：长批次如果超时，会等到整批结束才写出，容易丢进度。因此这次加入一个流式可恢复后台 worker：

- 每处理一条就追加到本地 raw JSONL；
- 每隔一批写一次 summary checkpoint；
- 断网、关机或 429 后，可以重新启动同一命令；
- 重新启动时会跳过已存在的 `comment_id`，继续补后面的记录。

## 启动命令

推荐直接在仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_reddit_pullpush_background.ps1
```

如果需要指定 Python，可用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_reddit_pullpush_background.ps1 -Python "C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
```

默认输入队列是：

```text
pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl
```

默认输出是本地文件：

```text
data/raw/reddit_bao_pullpush_full_stream.jsonl
data/raw/reddit_bao_pullpush_full_stream_summary.json
data/raw/logs/reddit_pullpush_background_*.log
```

`data/raw/` 已被 `.gitignore` 忽略，所以正文不会被提交到 Git。

## 默认参数

```text
--resume
--stream
--checkpoint-every 25
--sleep-seconds 1
--max-retries 5
--retry-sleep-seconds 15
--timeout 20
```

含义：

- `--stream`：逐条写出，不等整批结束；
- `--resume`：输出文件已存在时跳过已处理 `comment_id`；
- `--checkpoint-every 25`：每新增 25 条更新一次 summary；
- `--sleep-seconds 1`：降低 PullPush 429 风险；
- `--max-retries 5`：单条失败后最多重试 5 次。

## 看进度

看后台进程：

```powershell
Get-Process powershell | Select-Object Id,StartTime,Path
```

看日志：

```powershell
Get-ChildItem data\raw\logs\reddit_pullpush_background_*.log |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 |
  Get-Content -Tail 40
```

看 summary：

```powershell
Get-Content data\raw\reddit_bao_pullpush_full_stream_summary.json
```

建议关注：

```text
record_count
hydrated_count
hydrated_rate
status_counts
processed_new_count
skipped_existing_count
pending_count
```

## 当前种子

本地已经有：

```text
data/raw/reddit_bao_pullpush_balanced_600.jsonl
```

后台脚本默认会在 full-stream 输出不存在时，用这 600 条作为种子，避免从头重复抓。

如果 `data/raw/reddit_bao_pullpush_full_stream.jsonl` 已经存在，则不会覆盖，而是继续 resume。

## 研究用途

这个 worker 只解决数据采集工程问题，不改变研究主线。它的目标是给后续 Reddit-Text-Core benchmark 提供足量真实输入，使我们能比较：

- comment-only 条件；
- public policy card 条件；
- 我们的方法生成的 operational policy 条件。

真正进入论文的不是“爬虫”，而是这些条件下模型审核行为是否体现 policy-to-operation gap，以及我们的方法是否能缩小这个 gap。
