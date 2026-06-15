import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from regime_pilot.reddit_hydration import (
    MissingRedditCredentials,
    hydrate_queue,
    load_env_file,
    make_reddit_client_from_env,
    merge_env_file,
)
from regime_pilot.schema import load_jsonl


class _FakeComment:
    def __init__(self, body: str, permalink: str = "/r/science/comments/x/y/z") -> None:
        self.body = body
        self.permalink = permalink
        self.author = None
        self.created_utc = 123.0


class _FakeReddit:
    def __init__(self) -> None:
        self.requests = []

    def comment(self, id: str):
        self.requests.append(id)
        if id == "missing":
            raise RuntimeError("not found")
        return _FakeComment(body=f"text for {id}")


class RedditHydrationTests(unittest.TestCase):
    def test_hydrate_queue_writes_text_records_and_preserves_labels(self):
        queue = [
            {
                "case_id": "RB-test-en-science-000001",
                "comment_id": "abc123",
                "reddit_fullname": "t1_abc123",
                "subreddit": "science",
                "label": 1,
                "expected_decision": "remove",
                "policy_card_id": "reddit_science_p0_public_policy",
                "split": "test-en",
                "hydration_status": "pending",
            }
        ]
        client = _FakeReddit()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "hydrated.jsonl"

            summary = hydrate_queue(queue, output, client)
            records = load_jsonl(output)

        self.assertEqual(summary["hydrated"], 1)
        self.assertEqual(client.requests, ["abc123"])
        self.assertEqual(records[0]["text"], "text for abc123")
        self.assertEqual(records[0]["text_status"], "hydrated")
        self.assertEqual(records[0]["expected_decision"], "remove")

    def test_hydrate_queue_records_errors_without_stopping_the_batch(self):
        queue = [
            {
                "case_id": "RB-test-en-science-000001",
                "comment_id": "missing",
                "reddit_fullname": "t1_missing",
                "subreddit": "science",
                "label": 1,
                "expected_decision": "remove",
                "policy_card_id": "reddit_science_p0_public_policy",
                "split": "test-en",
                "hydration_status": "pending",
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "hydrated.jsonl"

            summary = hydrate_queue(queue, output, _FakeReddit())
            records = load_jsonl(output)

        self.assertEqual(summary["failed"], 1)
        self.assertEqual(records[0]["text_status"], "hydrate_error")
        self.assertIn("not found", records[0]["hydration_error"])

    def test_make_reddit_client_from_env_requires_credentials(self):
        with self.assertRaises(MissingRedditCredentials) as context:
            make_reddit_client_from_env({})

        self.assertIn("REDDIT_CLIENT_ID", str(context.exception))
        self.assertIn("REDDIT_CLIENT_SECRET", str(context.exception))
        self.assertIn("REDDIT_USER_AGENT", str(context.exception))

    def test_load_env_file_parses_comments_quotes_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.reddit.local"
            env_path.write_text(
                "\n"
                "# local credentials\n"
                "REDDIT_CLIENT_ID = abc123\n"
                "REDDIT_CLIENT_SECRET='secret value'\n"
                'REDDIT_USER_AGENT=\"regime research by u/example\"\n',
                encoding="utf-8",
            )

            values = load_env_file(env_path)

        self.assertEqual(
            values,
            {
                "REDDIT_CLIENT_ID": "abc123",
                "REDDIT_CLIENT_SECRET": "secret value",
                "REDDIT_USER_AGENT": "regime research by u/example",
            },
        )

    def test_merge_env_file_keeps_explicit_environment_over_file_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.reddit.local"
            env_path.write_text(
                "REDDIT_CLIENT_ID=file_id\n"
                "REDDIT_CLIENT_SECRET=file_secret\n"
                "REDDIT_USER_AGENT=file_agent\n",
                encoding="utf-8",
            )

            values = merge_env_file(
                env_path,
                base_env={
                    "REDDIT_CLIENT_ID": "env_id",
                    "OTHER": "kept",
                },
            )

        self.assertEqual(values["REDDIT_CLIENT_ID"], "env_id")
        self.assertEqual(values["REDDIT_CLIENT_SECRET"], "file_secret")
        self.assertEqual(values["REDDIT_USER_AGENT"], "file_agent")
        self.assertEqual(values["OTHER"], "kept")

    def test_cli_reports_missing_credentials_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = Path(tmp) / "queue.jsonl"
            queue_path.write_text(json.dumps({"comment_id": "abc123"}) + "\n", encoding="utf-8")
            output_path = Path(tmp) / "out.jsonl"
            env = os.environ.copy()
            env["PYTHONPATH"] = "pilot/src"
            env.pop("REDDIT_CLIENT_ID", None)
            env.pop("REDDIT_CLIENT_SECRET", None)
            env.pop("REDDIT_USER_AGENT", None)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "regime_pilot.reddit_hydration",
                    "--queue",
                    str(queue_path),
                    "--output",
                    str(output_path),
                    "--limit",
                    "1",
                ],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing Reddit API credentials", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
