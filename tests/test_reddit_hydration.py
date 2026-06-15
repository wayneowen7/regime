from pathlib import Path
import tempfile
import unittest

from regime_pilot.reddit_hydration import (
    MissingRedditCredentials,
    hydrate_queue,
    make_reddit_client_from_env,
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


if __name__ == "__main__":
    unittest.main()
