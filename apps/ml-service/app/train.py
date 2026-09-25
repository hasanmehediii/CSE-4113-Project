"""Train, evaluate, and save a replaceable complaint classifier: python -m app.train."""

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import joblib
import sklearn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from app.core.config import REPO_ROOT, get_settings
from app.models.classifier import CATEGORIES, make_pipeline, normalize_text

DEFAULT_DATASET = REPO_ROOT / "docs/dataset/drainage_complaints_bn.csv"


def read_dataset(path: Path) -> tuple[list[str], list[str], dict]:
    texts: dict[str, str] = {}
    ids: set[str] = set()
    rows = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not {"id", "text_bn", "category"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV must contain id, text_bn, and category columns.")
        for line, row in enumerate(reader, start=2):
            identifier = (row.get("id") or "").strip()
            text = normalize_text(row.get("text_bn") or "")
            category = (row.get("category") or "").strip()
            if not identifier or identifier in ids:
                raise ValueError(f"Row {line}: id must be nonempty and unique.")
            if not text or len(text) > 5000:
                raise ValueError(f"Row {line}: text_bn must contain 1 to 5000 characters.")
            if category not in CATEGORIES:
                raise ValueError(f"Row {line}: unknown category {category!r}.")
            if text in texts and texts[text] != category:
                raise ValueError(f"Row {line}: duplicate text has conflicting labels.")
            ids.add(identifier)
            texts[text] = category
            rows += 1
    counts = Counter(texts.values())
    if any(counts[category] < 2 for category in CATEGORIES):
        raise ValueError(
            "Provide at least two distinct complaint texts for each of the six categories."
        )
    return (
        list(texts),
        list(texts.values()),
        {
            "input_rows": rows,
            "unique_rows": len(texts),
            "duplicates_removed": rows - len(texts),
            "class_counts": dict(counts),
        },
    )


def train(dataset: Path, output: Path, data_source: str = "synthetic", seed: int = 42) -> dict:
    if data_source not in {"synthetic", "real", "mixed"}:
        raise ValueError("data_source must be synthetic, real, or mixed.")
    texts, labels, stats = read_dataset(dataset)
    test_count = max(len(CATEGORIES), math.ceil(len(texts) * 0.2))
    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=test_count, random_state=seed, stratify=labels
    )
    if set(y_train) != set(CATEGORIES) or set(y_test) != set(CATEGORIES):
        raise ValueError(
            "The holdout needs every category. Add more distinct examples per category."
        )
    evaluation_model = make_pipeline()
    evaluation_model.fit(x_train, y_train)
    predictions = evaluation_model.predict(x_test)
    timestamp = datetime.now(UTC)
    dataset_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    metadata = {
        "model_version": timestamp.strftime("%Y%m%dT%H%M%S%fZ") + "-" + dataset_hash[:12],
        "trained_at": timestamp.isoformat(),
        "data_source": data_source,
        "dataset": dataset.name,
        "dataset_sha256": dataset_hash,
        "sklearn_version": sklearn.__version__,
        "algorithm": "character TF-IDF (2-5 grams) + balanced logistic regression",
        "seed": seed,
        **stats,
        "evaluation": {
            "method": "stratified holdout after normalized exact-text deduplication",
            "train_rows": len(x_train),
            "test_rows": len(x_test),
            "accuracy": accuracy_score(y_test, predictions),
            "macro_f1": f1_score(y_test, predictions, average="macro"),
            "per_class": classification_report(
                y_test, predictions, labels=list(CATEGORIES), output_dict=True, zero_division=0
            ),
            "confusion_matrix_labels": list(CATEGORIES),
            "confusion_matrix": confusion_matrix(
                y_test, predictions, labels=list(CATEGORIES)
            ).tolist(),
            "limitations": (
                "Random holdout scores do not establish real-world accuracy. Synthetic template "
                "variants may occur in both splits. Evaluate on independent real complaints "
                "before drawing deployment conclusions. Confidence values are not calibrated."
            ),
        },
        "serving_model_training_rows": len(texts),
        "serving_model_note": "Refitted on all unique rows after holdout evaluation.",
    }
    final_model = make_pipeline()
    final_model.fit(texts, labels)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Failed training never overwrites a working model; publish the complete artifact atomically.
    with NamedTemporaryFile(dir=output.parent, suffix=".joblib", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(
            {"format_version": 1, "pipeline": final_model, "metadata": metadata}, temporary_path
        )
        os.replace(temporary_path, output)
    finally:
        temporary_path.unlink(missing_ok=True)
    output.with_suffix(".report.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=get_settings().model_path)
    parser.add_argument(
        "--data-source", choices=["synthetic", "real", "mixed"], default="synthetic"
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        metadata = train(args.dataset, args.output, args.data_source, args.seed)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Training failed: {error}\n")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(f"Model saved to {args.output}. Restart the ML service to load it.")


if __name__ == "__main__":
    main()
