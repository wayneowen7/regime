# PullPush Comment Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small, auditable PullPush-based resolver that turns existing Reddit comment IDs into raw text artifacts for local pilot use.

**Architecture:** Add one focused module under `pilot/src/regime_pilot/` that reads the existing hydration queue, resolves each comment ID through PullPush, writes raw hydrated records to ignored `data/raw/`, and writes a text-free summary JSON for reproducibility. Keep official Reddit/PRAW code unchanged.

**Tech Stack:** Python standard library (`urllib`, `json`, `hashlib`, `time`, `argparse`), existing `regime_pilot.schema.load_jsonl`, unittest.

---

### Task 1: Resolver Unit Tests

**Files:**
- Create: `tests/test_reddit_pullpush_resolver.py`
- Create after tests fail: `pilot/src/regime_pilot/reddit_pullpush_resolver.py`

- [ ] **Step 1: Write failing tests for mapping PullPush responses**

Create tests that verify:
- a normal PullPush result becomes `text_status=hydrated`;
- no data becomes `text_status=missing`;
- `[deleted]` and `[removed]` become `text_status=unavailable`;
- subreddit mismatch becomes `text_status=subreddit_mismatch` and does not keep text;
- summary counts do not include raw text.

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest tests.test_reddit_pullpush_resolver -v
```

Expected: fail because `regime_pilot.reddit_pullpush_resolver` does not exist.

- [ ] **Step 3: Implement minimal resolver**

Create `reddit_pullpush_resolver.py` with:
- `resolve_pullpush_record(queue_item, pullpush_data, retrieved_at)`;
- `summarize_resolved_records(records)`;
- `resolve_queue(queue_records, fetcher, output_path, summary_path, limit, sleep_seconds)`;
- CLI arguments: `--queue`, `--output`, `--summary`, `--limit`, `--sleep-seconds`, `--timeout`, `--user-agent`.

- [ ] **Step 4: Run resolver tests to verify pass**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest tests.test_reddit_pullpush_resolver -v
```

Expected: all tests pass.

### Task 2: Real Smoke Run

**Files:**
- Raw output: `data/raw/reddit_bao_pullpush_smoke100.jsonl` (ignored)
- Summary output: `pilot/results/reddit_bao_pullpush_smoke100_summary.json`

- [ ] **Step 1: Run PullPush smoke on 100 queued IDs**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m regime_pilot.reddit_pullpush_resolver `
  --queue pilot/data/reddit_bao/reddit_bao_hydration_queue.jsonl `
  --output data/raw/reddit_bao_pullpush_smoke100.jsonl `
  --summary pilot/results/reddit_bao_pullpush_smoke100_summary.json `
  --limit 100 `
  --sleep-seconds 0.2
```

- [ ] **Step 2: Inspect summary**

Confirm summary contains counts by `text_status`, source metadata, and no raw text bodies.

### Task 3: Documentation and Verification

**Files:**
- Create: `docs/research_notes/2026-06-16-reddit-pullpush-resolver-smoke.md`

- [ ] **Step 1: Write Chinese run note**

Document:
- why PullPush is a pilot fallback rather than final compliance source;
- smoke command;
- summary result;
- next decision gate for `Reddit-Text-Core`.

- [ ] **Step 2: Run full tests**

Run:

```powershell
$env:PYTHONPATH='pilot/src'
python -m unittest discover -s tests -v
```

- [ ] **Step 3: Commit and push**

Commit code, tests, plan, summary, and note. Do not commit `data/raw/`.
