from collections import Counter
import json
from pathlib import Path
import unittest

from regime_pilot.schema import load_jsonl


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "pilot" / "data" / "reddit_bao"


class RedditBaoArtifactTests(unittest.TestCase):
    def test_generated_manifest_matches_id_core_and_hydration_queue_counts(self):
        manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
        id_core = load_jsonl(DATA_DIR / "reddit_bao_id_core.jsonl")
        hydration_queue = load_jsonl(DATA_DIR / "reddit_bao_hydration_queue.jsonl")
        policy_cards = json.loads((DATA_DIR / "reddit_bao_policy_cards.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["record_count"], len(id_core))
        self.assertEqual(manifest["hydration_queue_count"], len(hydration_queue))
        self.assertEqual(manifest["policy_card_count"], len(policy_cards))
        self.assertEqual(manifest["split_counts"], {"train": 3000, "val": 600, "test-en": 1200})

    def test_id_core_is_balanced_by_split_subreddit_and_has_no_text(self):
        records = load_jsonl(DATA_DIR / "reddit_bao_id_core.jsonl")
        counts = Counter(
            (record["split"], record["subreddit"], record["label"])
            for record in records
        )

        expected_subreddits = {"science", "news", "worldnews", "space", "futurology", "nfl"}
        self.assertEqual({record["subreddit"] for record in records}, expected_subreddits)
        for split, expected_per_label in [("train", 250), ("val", 50), ("test-en", 100)]:
            for subreddit in expected_subreddits:
                self.assertEqual(counts[(split, subreddit, 0)], expected_per_label)
                self.assertEqual(counts[(split, subreddit, 1)], expected_per_label)

        for record in records:
            with self.subTest(case_id=record["case_id"]):
                self.assertIsNone(record["text"])
                self.assertEqual(record["text_status"], "unhydrated")
                self.assertIn(record["expected_decision"], {"allow", "remove"})

    def test_policy_cards_have_comment_rules_for_each_core_subreddit(self):
        cards = json.loads((DATA_DIR / "reddit_bao_policy_cards.json").read_text(encoding="utf-8"))

        self.assertEqual(len(cards), 6)
        for card in cards:
            with self.subTest(subreddit=card["subreddit"]):
                self.assertTrue(card["structured_comment_rules"])
                self.assertTrue(card["description"])
                self.assertEqual(
                    card["policy_card_id"],
                    f"reddit_{card['subreddit']}_p0_public_policy",
                )


if __name__ == "__main__":
    unittest.main()
