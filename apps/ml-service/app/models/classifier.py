"""Bengali complaint classifier. Only load artifacts produced by our training command."""

import unicodedata
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

CATEGORIES = (
    "blocked_drain",
    "open_manhole",
    "road_flooding",
    "waterlogging_recurring",
    "sewage_overflow",
    "other",
)


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def make_pipeline() -> Pipeline:
    # Character features retain Bengali vowel signs and handle modest spelling variation.
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), sublinear_tf=True)),
            (
                "classifier",
                LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
            ),
        ]
    )


class ComplaintClassifier:
    def __init__(self, pipeline: Pipeline, metadata: dict):
        self.pipeline = pipeline
        self.metadata = metadata

    @classmethod
    def load(cls, path: Path) -> "ComplaintClassifier":
        artifact = joblib.load(path)
        if artifact.get("format_version") != 1:
            raise ValueError("Unsupported model artifact format; retrain the classifier.")
        if artifact["metadata"]["sklearn_version"] != sklearn.__version__:
            raise ValueError(
                f"Model was trained with scikit-learn {artifact['metadata']['sklearn_version']}, "
                f"but this Python session uses {sklearn.__version__}. "
                "Select apps/ml-service/.venv/Scripts/python.exe as the notebook kernel "
                "and restart it. If the project environment was intentionally upgraded, "
                "retrain with ./train.ps1 and restart the service and notebook."
            )
        pipeline = artifact["pipeline"]
        if set(pipeline.classes_) != set(CATEGORIES):
            raise ValueError("Unexpected classifier categories; retrain the classifier.")
        return cls(pipeline, artifact["metadata"])

    def predict(self, text: str) -> dict:
        text = normalize_text(text)
        if not text:
            raise ValueError("Complaint text must not be blank.")
        probabilities = self.pipeline.predict_proba([text])[0]
        scores = dict(zip(self.pipeline.classes_.tolist(), probabilities.tolist(), strict=True))
        category = max(scores, key=scores.get)
        return {
            "predicted_category": category,
            "confidence": scores[category],
            "probabilities": scores,
            "model_version": self.metadata["model_version"],
            "data_source": self.metadata["data_source"],
        }
