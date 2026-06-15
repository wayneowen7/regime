# Reddit BAO 数据处理运行记录

日期：2026-06-15

## 当前目标

这一步不是训练模型，也不是上 agent RL / LoRA，而是把 Reddit moderation 数据集先整理成可复现的 benchmark 基础层：

1. `Reddit-ID-Core`：只包含公开 comment id、subreddit、label、split、policy card id；
2. `Policy Cards`：从公开 subreddit rules metadata 提取 public policy；
3. `Hydration Queue`：为后续合规获取 comment text 准备队列；
4. 明确 Text Acquisition Gate：没有 comment text 之前，不跑 LLM moderation benchmark。

## 数据源

本地缓存目录：

```text
.local_data/multilingual_content_mod
```

该目录来自公开仓库：

```text
https://github.com/mye1225/multilingual_content_mod
```

仓库 README 明确说明：公开版本只释放 comment ids；若要获得评论原文，需要通过 PRAW 按 id 获取，或填写作者提供的数据申请表并接受 DUA。

因此，本次提交不包含任何 Reddit 评论原文。

## 已生成文件

输出目录：

```text
pilot/data/reddit_bao
```

文件：

```text
pilot/data/reddit_bao/manifest.json
pilot/data/reddit_bao/reddit_bao_id_core.jsonl
pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl
pilot/data/reddit_bao/reddit_bao_policy_cards.json
```

当前规模：

| artifact | count |
|---|---:|
| ID-core records | 4,800 |
| hydration queue records | 4,800 |
| policy cards | 6 |

Split 规模：

| split | records |
|---|---:|
| train | 3,000 |
| val | 600 |
| test-en | 1,200 |

Subreddits：

```text
science, news, worldnews, space, futurology, nfl
```

每个 split 内，每个 subreddit 都按 label 平衡采样：

| split | per subreddit label=0 | per subreddit label=1 |
|---|---:|---:|
| train | 250 | 250 |
| val | 50 | 50 |
| test-en | 100 | 100 |

## 字段设计

`reddit_bao_id_core.jsonl` 的核心字段：

```json
{
  "case_id": "RB-train-science-000001",
  "dataset": "multilingual_content_mod",
  "source_view": "balanced/data-en",
  "split": "train",
  "subreddit": "science",
  "comment_id": "...",
  "reddit_fullname": "t1_...",
  "label": 0,
  "observed_label": "kept",
  "expected_decision": "allow",
  "policy_card_id": "reddit_science_p0_public_policy",
  "text_status": "unhydrated",
  "text": null
}
```

重要解释：

- `label=0` 映射为 `expected_decision=allow`；
- `label=1` 映射为 `expected_decision=remove`；
- 这只是 binary moderation label，不代表我们已经知道具体 removal rule；
- `text=null` 是刻意保留的 gate 标记，防止误以为当前已经可跑 LLM benchmark。

## 处理代码

新增模块：

```text
pilot/src/regime_pilot/reddit_dataset.py
pilot/src/regime_pilot/reddit_hydration.py
```

重新生成当前 artifacts：

```powershell
$env:PYTHONPATH='pilot/src'
& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m regime_pilot.reddit_dataset prepare `
  --dataset-root .local_data/multilingual_content_mod `
  --output-dir pilot/data/reddit_bao `
  --source-view balanced/data-en `
  --subreddits science news worldnews space futurology nfl `
  --train-size 500 `
  --val-size 100 `
  --test-size 200 `
  --seed 20260615
```

## Text Acquisition Gate

Hydration queue 文件：

```text
pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl
```

后续如果配置 Reddit API / PRAW 凭据，可以运行：

```powershell
$env:PYTHONPATH='pilot/src'
& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install praw

$env:REDDIT_CLIENT_ID='...'
$env:REDDIT_CLIENT_SECRET='...'
$env:REDDIT_USER_AGENT='regime-research-script by u/<your_username>'

& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m regime_pilot.reddit_hydration `
  --queue pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl `
  --output data/raw/reddit_bao_hydrated_comments.jsonl `
  --limit 20
```

注意：

- 当前本地 bundled Python 尚未安装 PRAW，且 `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT` 均未配置；
- 输出路径建议使用 `data/raw/`，该目录已经被 `.gitignore` 忽略；
- 不要把 hydrated comment text 提交到 GitHub；
- 先用 `--limit 20` smoke test，确认凭据、速率限制、删除评论比例；
- smoke 成功后再全量 hydrate 4,800 条。

## 验证

新增测试：

```text
tests/test_reddit_dataset.py
tests/test_reddit_hydration.py
tests/test_reddit_bao_artifacts.py
```

当前覆盖：

- policy card 是否能提取 comment rules；
- ID-core 是否能按 subreddit 和 label 平衡采样；
- hydration queue 是否只包含抓取文本所需字段；
- hydration 脚本是否能记录失败而不中断 batch；
- 生成 artifacts 是否没有评论原文；
- manifest 计数是否与实际文件一致。

## 对论文路线的意义

这一步解决的是 benchmark 地基问题：

```text
public policy card + real moderation labels + hidden comment text gate
```

它还没有证明我们的 BAO / policy compiler 方法有效，但它把下一步实验的上下界固定住了：

1. `comment-only`：只看评论文本；
2. `P0-rules`：评论文本 + structured comment rules；
3. `P0+description`：评论文本 + 完整 public policy card；
4. `ordinary rewrite`：普通 prompt 改写；
5. `BAO overlay / compiled policy`：边界变量、动作粒度、冲突优先级。

如果 `P0-rules` 和 `P0+description` 已经很强，说明 Reddit public rules 对这个数据集解释力足够，我们的方法需要在更细粒度 rule attribution 或 hard cases 上证明价值。

如果 `P0-rules` 明显不足，而 BAO overlay 能稳定提升，说明 policy-to-operation gap 在真实 moderation benchmark 上成立，论文主线会更稳。

## 下一步

优先级如下：

1. 获得 comment text：PRAW 凭据或原作者 DUA 数据；
2. 用 `--limit 20` 跑 hydration smoke；
3. 统计 deleted / unavailable / hydrated 比例；
4. 构造 `Reddit-Text-Core`；
5. 先跑 100-200 条 closed/open LLM 小矩阵；
6. 再决定是否做 BAO overlay、prompt compiler、data route 或 LoRA。
