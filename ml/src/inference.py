from pathlib import Path
import json
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "rf_final.joblib"
FEATURES_PATH = ARTIFACTS_DIR / "model_features.json"

DEFAULT_FEATURES = [
    "stylometric_distance",
    "behavior_similarity",
    "embedding_similarity",
    "shared_pgp",
    "shared_infra",
    "shared_handle_with_overlap",
    "evidence_count",
    "same_kmeans_cluster",
]

_model = None
_feature_names = None


def _get_model():
    global _model, _feature_names
    if _model is not None:
        return _model, _feature_names

    if MODEL_PATH.exists() and FEATURES_PATH.exists():
        try:
            _model = joblib.load(MODEL_PATH)
            with FEATURES_PATH.open("r", encoding="utf-8") as f:
                _feature_names = json.load(f)
            return _model, _feature_names
        except Exception:
            pass

    # Try training on the fly
    try:
        from ..train_model import train_and_save_model
        _model = train_and_save_model()
        _feature_names = DEFAULT_FEATURES
        return _model, _feature_names
    except Exception:
        pass

    return None, DEFAULT_FEATURES


def confidence_band(probability: float) -> str:
    if probability >= 0.75:
        return "high"
    if probability >= 0.50:
        return "moderate"
    if probability >= 0.20:
        return "weak"
    return "very_low"


def predict_relationship(
    actor_a: str,
    actor_b: str,
    features: dict,
) -> dict:
    model, feature_names = _get_model()
    feature_names = feature_names or DEFAULT_FEATURES

    # Compute probability
    if model is not None:
        try:
            feature_row = pd.DataFrame(
                [[features.get(f, 0.0) for f in feature_names]],
                columns=feature_names,
            )
            probability = float(model.predict_proba(feature_row)[0, 1])
        except Exception:
            probability = 0.5
    else:
        # Heuristic fallback calculation
        score = (
            0.30 * float(features.get("shared_pgp", 0))
            + 0.25 * float(features.get("shared_infra", 0))
            + 0.20 * float(features.get("shared_handle_with_overlap", 0))
            + 0.15 * float(features.get("behavior_similarity", 0.5))
            + 0.10 * (1.0 - min(float(features.get("stylometric_distance", 1.0)), 1.0))
        )
        probability = max(0.0, min(1.0, score))

    return {
        "persona_a": str(actor_a),
        "persona_b": str(actor_b),
        "relationship_probability": round(probability, 3),
        "confidence_band": confidence_band(probability),
        "features": features,
        "model_version": "rf-final-v1",
        "limitations": [
            "This is an analytical similarity score.",
            "It does not establish real-world identity.",
            "Some features may be unavailable in the MVP dataset.",
        ],
    }