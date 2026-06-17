from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable


DATASET_SPECS: dict[str, dict[str, str]] = {
    "aegis2": {
        "source_type": "hf",
        "dataset_id": "nvidia/Aegis-AI-Content-Safety-Dataset-2.0",
    },
    "wildguardmix": {
        "source_type": "hf",
        "dataset_id": "allenai/wildguardmix",
    },
    "dynabench": {
        "source_type": "hf",
        "dataset_id": "tomg-group-umd/DynaBench",
    },
    "barred": {
        "source_type": "hf",
        "dataset_id": "Plurai/BARRED",
    },
}

TEXT_FIELD_MARKERS = {
    "answer",
    "body",
    "comment",
    "content",
    "conversation",
    "input",
    "instruction",
    "message",
    "output",
    "prompt",
    "query",
    "question",
    "response",
    "text",
    "transcript",
}

LABEL_FIELD_MARKERS = {
    "category",
    "harm",
    "harmful",
    "label",
    "risk",
    "safe",
    "safety",
    "toxicity",
    "unsafe",
    "violate",
    "violation",
}

POLICY_FIELD_MARKERS = {
    "definition",
    "guideline",
    "policy",
    "rule",
    "taxonomy",
}

ACTION_FIELD_MARKERS = {
    "action",
    "decision",
    "intervention",
    "moderation_action",
    "refusal",
    "refuse",
}


def write_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(_json_safe(record), ensure_ascii=False, sort_keys=True) + "\n")


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def infer_field_role(field_name: str) -> str:
    normalized = field_name.lower()
    if any(marker in normalized for marker in POLICY_FIELD_MARKERS):
        return "policy"
    if any(marker in normalized for marker in ACTION_FIELD_MARKERS):
        return "action"
    if any(marker in normalized for marker in LABEL_FIELD_MARKERS):
        return "label"
    if any(marker in normalized for marker in TEXT_FIELD_MARKERS):
        return "text"
    return "metadata"


def _value_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _categorical_top_values(values: list[Any], role: str) -> dict[str, int]:
    if role in {"text", "policy"}:
        return {}
    counter: Counter[str] = Counter()
    for value in values:
        if isinstance(value, (str, int, float, bool)) or value is None:
            rendered = str(value)
            if len(rendered) <= 80:
                counter[rendered] += 1
    if not counter or len(counter) > 30:
        return {}
    return {key: counter[key] for key, _ in counter.most_common(15)}


def build_dataset_profile(
    dataset_name: str,
    dataset_id: str,
    records: list[dict[str, Any]],
    split_counts: dict[str, int],
    status: str = "ok",
    error: str | None = None,
) -> dict[str, Any]:
    fields = sorted({str(key) for record in records for key in record})
    field_roles = {field: infer_field_role(field) for field in fields}
    field_profiles: dict[str, dict[str, Any]] = {}
    for field in fields:
        values = [record.get(field) for record in records if field in record]
        role = field_roles[field]
        type_counts = Counter(_value_type_name(value) for value in values)
        non_empty = sum(value not in (None, "", [], {}) for value in values)
        string_lengths = [len(value) for value in values if isinstance(value, str)]
        profile: dict[str, Any] = {
            "role": role,
            "present_count": len(values),
            "non_empty_count": non_empty,
            "type_counts": {key: type_counts[key] for key in sorted(type_counts)},
        }
        if string_lengths:
            profile["string_length"] = {
                "min": min(string_lengths),
                "max": max(string_lengths),
                "mean": round(sum(string_lengths) / len(string_lengths), 2),
            }
        top_values = _categorical_top_values(values, role)
        if top_values:
            profile["top_values"] = top_values
        field_profiles[field] = profile

    role_counts = Counter(field_roles.values())
    fit = {
        "has_text": role_counts["text"] > 0,
        "has_label": role_counts["label"] > 0,
        "has_policy": role_counts["policy"] > 0,
        "has_action_signal": role_counts["action"] > 0,
        "policy_to_operation_candidate": role_counts["text"] > 0 and role_counts["label"] > 0,
        "native_policy_conditioned_candidate": role_counts["policy"] > 0
        and role_counts["text"] > 0
        and role_counts["label"] > 0,
    }
    return {
        "dataset_name": dataset_name,
        "dataset_id": dataset_id,
        "status": status,
        "error": error,
        "sample_count": len(records),
        "split_counts": split_counts,
        "fields": fields,
        "field_roles": field_roles,
        "role_counts": {key: role_counts[key] for key in sorted(role_counts)},
        "field_profiles": field_profiles,
        "fit": fit,
        "contains_raw_text": False,
    }


def write_dataset_sample_outputs(
    dataset_name: str,
    dataset_id: str,
    records: list[dict[str, Any]],
    split_counts: dict[str, int],
    raw_output_path: str | Path,
    summary_output_path: str | Path,
) -> dict[str, Any]:
    write_jsonl(raw_output_path, records)
    profile = build_dataset_profile(
        dataset_name=dataset_name,
        dataset_id=dataset_id,
        records=records,
        split_counts=split_counts,
    )
    profile["raw_output_path"] = str(raw_output_path)
    profile["summary_output_path"] = str(summary_output_path)
    write_json(summary_output_path, profile)
    return profile


def _candidate_configs(dataset_id: str, max_configs: int) -> list[str | None]:
    from datasets import get_dataset_config_names

    try:
        configs = get_dataset_config_names(dataset_id)
    except Exception:
        return [None]
    if not configs:
        return [None]
    normalized: list[str | None] = [None if config == "default" else config for config in configs]
    return normalized[:max_configs]


def _candidate_splits(dataset_id: str, config_name: str | None) -> list[str]:
    from datasets import get_dataset_split_names

    try:
        kwargs: dict[str, Any] = {}
        if config_name is not None:
            kwargs["config_name"] = config_name
        splits = get_dataset_split_names(dataset_id, **kwargs)
    except Exception:
        try:
            splits = get_dataset_split_names(dataset_id)
        except Exception:
            return ["train"]
    preferred = ["train", "test", "validation", "dev"]
    ordered = [split for split in preferred if split in splits]
    ordered.extend(split for split in splits if split not in ordered)
    return ordered or ["train"]


def load_hf_sample(
    dataset_id: str,
    sample_size: int,
    max_configs: int = 32,
    max_splits_per_config: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    from datasets import load_dataset

    records: list[dict[str, Any]] = []
    split_counts: dict[str, int] = {}
    errors: list[str] = []
    for config_name in _candidate_configs(dataset_id, max_configs=max_configs):
        for split in _candidate_splits(dataset_id, config_name)[:max_splits_per_config]:
            if len(records) >= sample_size:
                return records, split_counts, errors
            split_key = f"{config_name or 'default'}:{split}"
            try:
                kwargs: dict[str, Any] = {
                    "split": split,
                    "streaming": True,
                }
                if config_name is not None:
                    kwargs["name"] = config_name
                dataset = load_dataset(dataset_id, **kwargs)
                for item in dataset:
                    records.append(_json_safe(dict(item)))
                    split_counts[split_key] = split_counts.get(split_key, 0) + 1
                    if len(records) >= sample_size:
                        return records, split_counts, errors
            except Exception as exc:
                errors.append(f"{split_key}: {type(exc).__name__}: {exc}")
    return records, split_counts, errors


def bootstrap_dataset(
    dataset_name: str,
    spec: dict[str, str],
    sample_size: int,
    raw_dir: str | Path,
    summary_dir: str | Path,
) -> dict[str, Any]:
    dataset_id = spec["dataset_id"]
    raw_path = Path(raw_dir) / f"{dataset_name}_sample{sample_size}.jsonl"
    summary_path = Path(summary_dir) / f"{dataset_name}_sample{sample_size}_summary.json"
    try:
        if spec.get("source_type") != "hf":
            raise ValueError(f"unsupported source_type: {spec.get('source_type')}")
        records, split_counts, errors = load_hf_sample(dataset_id, sample_size=sample_size)
        if not records:
            raise RuntimeError("; ".join(errors) if errors else "no records loaded")
        profile = write_dataset_sample_outputs(
            dataset_name=dataset_name,
            dataset_id=dataset_id,
            records=records,
            split_counts=split_counts,
            raw_output_path=raw_path,
            summary_output_path=summary_path,
        )
        profile["loader_errors"] = errors
        write_json(summary_path, profile)
        return profile
    except Exception as exc:
        profile = build_dataset_profile(
            dataset_name=dataset_name,
            dataset_id=dataset_id,
            records=[],
            split_counts={},
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
        )
        profile["raw_output_path"] = str(raw_path)
        profile["summary_output_path"] = str(summary_path)
        write_json(summary_path, profile)
        return profile


def bootstrap_datasets(
    dataset_names: list[str],
    sample_size: int,
    raw_dir: str | Path,
    summary_dir: str | Path,
    index_path: str | Path,
) -> dict[str, Any]:
    profiles = []
    for dataset_name in dataset_names:
        if dataset_name not in DATASET_SPECS:
            raise ValueError(f"unknown dataset: {dataset_name}")
        profiles.append(
            bootstrap_dataset(
                dataset_name=dataset_name,
                spec=DATASET_SPECS[dataset_name],
                sample_size=sample_size,
                raw_dir=raw_dir,
                summary_dir=summary_dir,
            )
        )
    index = {
        "sample_size": sample_size,
        "datasets": profiles,
        "contains_raw_text": False,
    }
    write_json(index_path, index)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap public moderation datasets for feasibility checks.")
    parser.add_argument("--datasets", nargs="+", default=list(DATASET_SPECS))
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--raw-dir", default="data/raw/dataset_bootstrap")
    parser.add_argument("--summary-dir", default="pilot/results/dataset_bootstrap")
    parser.add_argument("--index", default="pilot/results/dataset_bootstrap_index.json")
    args = parser.parse_args()

    index = bootstrap_datasets(
        dataset_names=args.datasets,
        sample_size=args.sample_size,
        raw_dir=args.raw_dir,
        summary_dir=args.summary_dir,
        index_path=args.index,
    )
    print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
