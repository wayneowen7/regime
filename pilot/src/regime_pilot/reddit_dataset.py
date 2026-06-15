from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable


DATASET_NAME = "multilingual_content_mod"
DEFAULT_SUBREDDITS = ("science", "news", "worldnews", "space", "futurology", "nfl")
DEFAULT_SPLIT_SIZES = {"train": 500, "val": 100, "test-en": 200}
LABEL_TO_DECISION = {0: "allow", 1: "remove"}
LABEL_TO_OBSERVED = {0: "kept", 1: "removed"}


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _normalise_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": _clean_text(rule.get("kind")),
        "short_name": _clean_text(rule.get("short_name")),
        "description": _clean_text(rule.get("description")),
        "violation_reason": _clean_text(rule.get("violation_reason")),
        "priority": rule.get("priority"),
        "created_utc": rule.get("created_utc"),
    }


def build_policy_cards(
    rules_snapshot_root: str | Path,
    subreddits: Iterable[str] = DEFAULT_SUBREDDITS,
) -> list[dict[str, Any]]:
    root = Path(rules_snapshot_root)
    cards: list[dict[str, Any]] = []
    for subreddit in subreddits:
        metadata_path = root / subreddit / "subreddit_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        raw_rules = metadata.get("rules", {}).get("rules", [])
        structured_rules = [_normalise_rule(rule) for rule in raw_rules]
        comment_rules = [rule for rule in structured_rules if rule["kind"] == "comment"]
        link_rules = [rule for rule in structured_rules if rule["kind"] == "link"]
        cards.append(
            {
                "policy_card_id": f"reddit_{subreddit}_p0_public_policy",
                "dataset": DATASET_NAME,
                "subreddit": subreddit,
                "display_name": _clean_text(metadata.get("display_name", subreddit)),
                "title": _clean_text(metadata.get("title")),
                "description": _clean_text(metadata.get("description")),
                "structured_comment_rules": comment_rules,
                "structured_link_rules": link_rules,
                "site_rules": metadata.get("rules", {}).get("site_rules", []),
                "source_snapshot": root.name,
                "source_path": str(Path("rules") / root.name / subreddit / "subreddit_metadata.json"),
                "policy_views": [
                    "P0_structured_comment_rules",
                    "P1_subreddit_description",
                    "P2_site_rules",
                ],
                "text_scope_note": "Rules are public policy context; comment text is not included in this card.",
            }
        )
    return cards


def _load_pickle_dataframe(path: Path):
    try:
        import pandas as pd  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Reading Reddit split pickle files requires pandas. Use the bundled "
            "Codex Python runtime or install pandas in the active environment."
        ) from exc
    return pd.read_pickle(path)


def _split_pickle_path(dataset_root: Path, source_view: str, split_name: str) -> Path:
    filename = split_name if split_name.endswith(".pkl") else f"{split_name}.pkl"
    return dataset_root / Path(source_view) / filename


def _label_allocation(samples_per_subreddit: int) -> dict[int, int]:
    if samples_per_subreddit < 2:
        raise ValueError("samples_per_subreddit must be at least 2 for a balanced sample")
    base = samples_per_subreddit // 2
    allocation = {0: base, 1: base}
    if samples_per_subreddit % 2:
        allocation[1] += 1
    return allocation


def _sample_label_rows(frame, label: int, size: int, seed: int):
    label_frame = frame[frame["label"] == label]
    if len(label_frame) < size:
        raise ValueError(
            f"Not enough rows for subreddit={frame.iloc[0]['subreddit']} "
            f"label={label}: need {size}, found {len(label_frame)}"
        )
    sampled = label_frame.sample(n=size, random_state=seed)
    return sampled.sort_values("id")


def build_id_core(
    dataset_root: str | Path,
    source_view: str,
    split_name: str,
    subreddits: Iterable[str] = DEFAULT_SUBREDDITS,
    samples_per_subreddit: int = 200,
    seed: int = 20260615,
) -> list[dict[str, Any]]:
    import pandas as pd

    root = Path(dataset_root)
    split_path = _split_pickle_path(root, source_view, split_name)
    frame = _load_pickle_dataframe(split_path)
    required_columns = {"label", "id", "subreddit"}
    missing = required_columns - set(frame.columns)
    if missing:
        raise ValueError(f"{split_path} missing required columns: {sorted(missing)}")

    target_subreddits = list(subreddits)
    frame = frame[frame["subreddit"].isin(target_subreddits)].copy()
    allocation = _label_allocation(samples_per_subreddit)
    records: list[dict[str, Any]] = []
    sequence = 1
    for subreddit_index, subreddit in enumerate(target_subreddits):
        subreddit_frame = frame[frame["subreddit"] == subreddit]
        if subreddit_frame.empty:
            raise ValueError(f"No rows found for subreddit={subreddit} in {split_path}")
        sampled_parts = []
        for label, size in allocation.items():
            sampled_parts.append(
                _sample_label_rows(
                    subreddit_frame,
                    label=label,
                    size=size,
                    seed=seed + subreddit_index * 10 + label,
                )
            )
        sampled = pd.concat(sampled_parts).sort_values(["label", "id"])
        for row in sampled.itertuples(index=False):
            label = int(row.label)
            comment_id = str(row.id)
            records.append(
                {
                    "case_id": f"RB-{split_name}-{subreddit}-{sequence:06d}",
                    "dataset": DATASET_NAME,
                    "source_view": source_view,
                    "split": split_name,
                    "subreddit": subreddit,
                    "comment_id": comment_id,
                    "reddit_fullname": f"t1_{comment_id}",
                    "label": label,
                    "observed_label": LABEL_TO_OBSERVED[label],
                    "expected_decision": LABEL_TO_DECISION[label],
                    "policy_card_id": f"reddit_{subreddit}_p0_public_policy",
                    "text_status": "unhydrated",
                    "text": None,
                }
            )
            sequence += 1
    return records


def build_hydration_queue(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "case_id",
        "comment_id",
        "reddit_fullname",
        "subreddit",
        "label",
        "expected_decision",
        "policy_card_id",
        "split",
    ]
    queue = []
    for record in records:
        item = {field: record[field] for field in fields}
        item["hydration_status"] = "pending"
        queue.append(item)
    return queue


def find_rules_snapshot_root(dataset_root: str | Path, snapshot: str | None = None) -> Path:
    rules_root = Path(dataset_root) / "rules"
    if snapshot is not None:
        return rules_root / snapshot
    snapshots = sorted(path for path in rules_root.iterdir() if path.is_dir())
    if not snapshots:
        raise FileNotFoundError(f"No rules snapshots found under {rules_root}")
    return snapshots[-1]


def prepare_reddit_bao_dataset(
    dataset_root: str | Path,
    output_dir: str | Path,
    source_view: str = "balanced/data-en",
    subreddits: Iterable[str] = DEFAULT_SUBREDDITS,
    split_sizes: dict[str, int] | None = None,
    seed: int = 20260615,
    rules_snapshot: str | None = None,
) -> dict[str, Any]:
    output_root = Path(output_dir)
    target_subreddits = list(subreddits)
    sizes = split_sizes or DEFAULT_SPLIT_SIZES
    rules_snapshot_root = find_rules_snapshot_root(dataset_root, rules_snapshot)

    policy_cards = build_policy_cards(rules_snapshot_root, target_subreddits)
    id_core_records: list[dict[str, Any]] = []
    split_counts: dict[str, int] = {}
    for split_name, split_size in sizes.items():
        split_records = build_id_core(
            dataset_root=dataset_root,
            source_view=source_view,
            split_name=split_name,
            subreddits=target_subreddits,
            samples_per_subreddit=split_size,
            seed=seed,
        )
        id_core_records.extend(split_records)
        split_counts[split_name] = len(split_records)

    hydration_queue = build_hydration_queue(id_core_records)
    manifest = {
        "dataset": DATASET_NAME,
        "source_view": source_view,
        "subreddits": target_subreddits,
        "rules_snapshot": rules_snapshot_root.name,
        "split_sizes_requested": sizes,
        "split_counts": split_counts,
        "record_count": len(id_core_records),
        "policy_card_count": len(policy_cards),
        "hydration_queue_count": len(hydration_queue),
        "text_status": "unhydrated",
        "outputs": {
            "id_core": "reddit_bao_id_core.jsonl",
            "hydration_queue": "reddit_bao_hydration_queue.jsonl",
            "policy_cards": "reddit_bao_policy_cards.json",
            "manifest": "manifest.json",
        },
    }

    write_jsonl(output_root / "reddit_bao_id_core.jsonl", id_core_records)
    write_jsonl(output_root / "reddit_bao_hydration_queue.jsonl", hydration_queue)
    write_json(output_root / "reddit_bao_policy_cards.json", policy_cards)
    write_json(output_root / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Reddit BAO benchmark data artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--dataset-root", default=".local_data/multilingual_content_mod")
    prepare.add_argument("--output-dir", default="pilot/data/reddit_bao")
    prepare.add_argument("--source-view", default="balanced/data-en")
    prepare.add_argument("--subreddits", nargs="+", default=list(DEFAULT_SUBREDDITS))
    prepare.add_argument("--train-size", type=int, default=DEFAULT_SPLIT_SIZES["train"])
    prepare.add_argument("--val-size", type=int, default=DEFAULT_SPLIT_SIZES["val"])
    prepare.add_argument("--test-size", type=int, default=DEFAULT_SPLIT_SIZES["test-en"])
    prepare.add_argument("--seed", type=int, default=20260615)
    prepare.add_argument("--rules-snapshot")
    args = parser.parse_args()

    if args.command == "prepare":
        manifest = prepare_reddit_bao_dataset(
            dataset_root=args.dataset_root,
            output_dir=args.output_dir,
            source_view=args.source_view,
            subreddits=args.subreddits,
            split_sizes={
                "train": args.train_size,
                "val": args.val_size,
                "test-en": args.test_size,
            },
            seed=args.seed,
            rules_snapshot=args.rules_snapshot,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
