# Reddit-Text-Core v0 运行记录

日期：2026-06-16

## 目标

把 Reddit 数据路线从“持续采集正文”推进到一个可运行的最小 benchmark：

1. 从本地 PullPush hydrated raw 中抽取 `Reddit-Text-Core v0`；
2. 保持正文与 `case_id / comment_id / label / expected_decision / policy_card_id` 对齐；
3. 支持两个最小条件：
   - `comment_only`：只给评论文本；
   - `public_policy`：给评论文本和 subreddit public policy card；
4. 输出 text-free summary，避免 Reddit 正文进入 Git。

## 已实现组件

新增代码：

```text
pilot/src/regime_pilot/reddit_text_core.py
pilot/src/regime_pilot/run_reddit_text_benchmark.py
```

新增测试：

```text
tests/test_reddit_text_core.py
```

新增远端脚本：

```text
scripts/run_2026_06_16_reddit_text_core_v0_remote.ps1
```

## v0 快照

构造命令：

```powershell
$env:PYTHONPATH='pilot/src'
python -m regime_pilot.reddit_text_core `
  --raw data/raw/reddit_bao_pullpush_full_stream.jsonl `
  --output data/raw/reddit_text_core_v0.jsonl `
  --summary pilot/results/reddit_text_core_v0_summary.json `
  --samples-per-subreddit 25 `
  --subreddits science news worldnews space futurology nfl
```

本地正文输出：

```text
data/raw/reddit_text_core_v0.jsonl
```

Git 中只保存无正文 summary：

```text
pilot/results/reddit_text_core_v0_summary.json
```

## 当前结果

本次 v0 选取 6 个 subreddit，每个 subreddit 25 条，共 150 条：

| subreddit | allow | remove | total |
|---|---:|---:|---:|
| science | 24 | 1 | 25 |
| news | 24 | 1 | 25 |
| worldnews | 25 | 0 | 25 |
| space | 25 | 0 | 25 |
| futurology | 25 | 0 | 25 |
| nfl | 25 | 0 | 25 |

合计：

```text
allow = 148
remove = 2
total = 150
```

## 关键发现

这版 v0 跑起来了，但它同时暴露出一个很重要的问题：

> 通过 PullPush 可取回的正文强烈偏向 kept / allow 样本；removed 样本大量变成 `[removed]` 或 unavailable。

这意味着当前 `Reddit-Text-Core v0` 可以用于验证 pipeline，但还不能直接作为论文主实验，因为 always-allow baseline 已经会非常高：

```text
always-allow accuracy = 148 / 150 = 98.67%
```

这不是坏事，反而是 Reddit 路线的第一个 pain check：

- 如果 removed comments 的正文不可恢复，那么 Reddit public ID 数据不能天然支撑二分类审核 benchmark；
- 后续必须要么继续寻找可恢复的 removed text；
- 要么转成 kept-only 的 policy interpretation / false-positive risk benchmark；
- 要么换一个保留 text 的审核数据源。

## Benchmark runner

真实模型运行命令：

```powershell
$env:PYTHONPATH='pilot/src'
python -m regime_pilot.run_reddit_text_benchmark `
  --cases data/raw/reddit_text_core_v0.jsonl `
  --policy-cards pilot/data/reddit_bao/reddit_bao_policy_cards.json `
  --model qwen2.5:7b `
  --conditions comment_only,public_policy `
  --limit-cases 30 `
  --output-full data/raw/reddit_text_benchmark_v0_full.json `
  --summary pilot/results/reddit_text_benchmark_v0_summary.json
```

注意：

- `output-full` 放在 `data/raw/`，不进 Git；
- `summary` 是 text-free，可以进 Git；
- runner 不把 prompt 或 comment text 写入 summary。

## 远端状态

本地没有可用 Ollama。

尝试连接远端：

```text
ssh lenovo@10.147.18.151
```

结果：

```text
Connection timed out
Ping timed out
```

因此本轮还没有拿到真实 LLM 结果。远端恢复后，直接运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_2026_06_16_reddit_text_core_v0_remote.ps1
```

该脚本会上传代码、测试、`data/raw/reddit_text_core_v0.jsonl`，并在远端跑：

```text
qwen2.5:7b
llama3.2:latest
```

每个模型先跑 30 cases 的 `comment_only` 和 `public_policy`。

## 当前判断

Reddit v0 的价值不是已经证明方法有效，而是快速暴露了数据路线的现实约束：

1. pipeline 可运行；
2. public policy card 条件可评估；
3. 当前 text acquisition 对 removed label 严重不友好；
4. 直接做 allow/remove accuracy 会被 label imbalance 污染；
5. 下一步需要优先解决 negative/removed text acquisition，或者重新定义 Reddit 子任务。

## 下一步

建议下一步不是立刻扩大 LLM 矩阵，而是先做数据可用性修复：

1. 构造 label=1 优先采集队列；
2. 统计所有 label=1 的 hydrated / unavailable / error 比例；
3. 如果 label=1 正文恢复率持续很低，停止把 Reddit 当作主二分类 benchmark；
4. 保留 Reddit 作为 policy-card / public-rules 条件下的可解释性或 false-positive benchmark；
5. 同时寻找保留 removed text 的审核数据源。
