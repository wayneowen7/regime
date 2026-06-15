# Reddit PRAW OAuth2 设置记录

日期：2026-06-15

## 结论

我们当前只需要读取公开 Reddit comment text，不需要代表用户发帖、投票或改账号状态。因此优先使用 PRAW 的 read-only client credentials 路线：

```text
client_id + client_secret + user_agent
```

不需要先做复杂的网页登录授权码回调。

## 已完成

本地 Codex bundled Python 已安装 PRAW：

```powershell
& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install praw
```

安装版本：

```text
praw==8.0.1
```

项目代码已支持本地 env 文件：

```text
pilot/src/regime_pilot/reddit_hydration.py --env-file .env.reddit.local
```

模板文件：

```text
config/reddit_api.env.example
```

真实密钥文件建议放在 repo 根目录：

```text
.env.reddit.local
```

该文件匹配 `.gitignore` 中的 `.env.*`，不会被提交。

## 你需要在 Reddit 上做的事

打开：

```text
https://www.reddit.com/prefs/apps
```

创建 app：

```text
name: regime-research-hydration
type: script
description: research script for hydrating public comment ids
about url: 可留空
redirect uri: http://localhost:8080
```

创建后页面上会有：

```text
client_id: app 名称下面那串短 ID
client_secret: secret 后面的长字符串
```

然后把模板复制成：

```text
.env.reddit.local
```

内容示例：

```text
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=regime-research-hydration/0.1 by u/你的Reddit用户名
```

`USER_AGENT` 不要写默认字符串，要包含项目名和 Reddit 用户名，方便 Reddit API 识别来源。

## Smoke test

先跑 20 条，不要直接全量：

```powershell
$env:PYTHONPATH='pilot/src'

& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m regime_pilot.reddit_hydration `
  --env-file .env.reddit.local `
  --queue pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl `
  --output data/raw/reddit_bao_hydrated_comments_smoke20.jsonl `
  --limit 20
```

预期输出类似：

```json
{
  "attempted": 20,
  "failed": 0,
  "hydrated": 20
}
```

如果出现失败，不一定是 OAuth 错，也可能是评论已删除、私有、不可访问或 Reddit API 临时拒绝。

## 全量 hydration

Smoke 通过后再跑全量：

```powershell
$env:PYTHONPATH='pilot/src'

& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m regime_pilot.reddit_hydration `
  --env-file .env.reddit.local `
  --queue pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl `
  --output data/raw/reddit_bao_hydrated_comments.jsonl
```

注意：

- `data/raw/` 已被 `.gitignore` 忽略；
- 不要提交 hydrated comment text；
- full run 后先统计 `text_status=hydrated` 与 `text_status=hydrate_error` 比例；
- 再决定是否构造 `Reddit-Text-Core`。

## 常见错误

### Missing Reddit API credentials

说明 `.env.reddit.local` 不存在、路径写错，或缺少以下字段：

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
```

### PRAW is required for hydration

说明当前 Python 环境没有安装 PRAW。使用 Codex bundled Python 运行：

```powershell
& 'C:\Users\wayne\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m pip install praw
```

### 401 / invalid_client

通常是 `client_id` 或 `client_secret` 填错。Reddit app 页面中，`client_id` 是 app 名称下面那串短 ID，不是 app name。

### 429 / rate limit

说明请求太快或 Reddit 限流。先降低 batch，必要时后续给 hydration 脚本加 sleep / retry。

## 当前状态

当前机器已经安装 PRAW，但还没有真实 Reddit 凭据，因此还不能 hydrate 文本。

下一步是创建 Reddit app，并把三项值写入 `.env.reddit.local`。
