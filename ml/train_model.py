from pathlib import Path
import json
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"
ARTIFACTS_DIR = PROJECT_ROOT / "ml" / "artifacts"

FEATURE_NAMES = [
    "stylometric_distance",
    "behavior_similarity",
    "embedding_similarity",
    "shared_pgp",
    "shared_infra",
    "shared_handle_with_overlap",
    "evidence_count",
    "same_kmeans_cluster",
]


def generate_training_data(n_samples: int = 2000):
    """
    Generate ground-truth aligned training dataset for Dark Web persona attribution.
    Simulates positive pairs (same entity with high similarity, shared PGP/infra/handles)
    and negative pairs (independent actors with low similarity, distinct infra).
    """
    np.random.seed(42)

    # Positive samples (same actor / alias)
    n_pos = n_samples // 2
    pos_data = {
        "stylometric_distance": np.random.beta(1.5, 4.0, size=n_pos) * 1.5,  # Low distance
        "behavior_similarity": np.random.beta(4.0, 1.5, size=n_pos),        # High similarity
        "embedding_similarity": np.random.beta(4.5, 1.5, size=n_pos),       # High embedding similarity
        "shared_pgp": np.random.binomial(1, 0.45, size=n_pos),              # Often shared
        "shared_infra": np.random.binomial(1, 0.60, size=n_pos),            # Often shared
        "shared_handle_with_overlap": np.random.binomial(1, 0.50, size=n_pos),
        "evidence_count": np.random.poisson(lam=4.5, size=n_pos),
        "same_kmeans_cluster": np.random.binomial(1, 0.85, size=n_pos),
    }
    df_pos = pd.DataFrame(pos_data)
    df_pos["label"] = 1

    # Negative samples (different actors)
    n_neg = n_samples - n_pos
    neg_data = {
        "stylometric_distance": np.random.beta(4.0, 1.5, size=n_neg) * 2.5,  # High distance
        "behavior_similarity": np.random.beta(1.5, 4.0, size=n_neg),        # Low similarity
        "embedding_similarity": np.random.beta(1.5, 4.0, size=n_neg),       # Low embedding similarity
        "shared_pgp": np.random.binomial(1, 0.02, size=n_neg),              # Very rarely shared
        "shared_infra": np.random.binomial(1, 0.05, size=n_neg),            # Rarely shared
        "shared_handle_with_overlap": np.random.binomial(1, 0.03, size=n_neg),
        "evidence_count": np.random.poisson(lam=0.5, size=n_neg),
        "same_kmeans_cluster": np.random.binomial(1, 0.15, size=n_neg),
    }
    df_neg = pd.DataFrame(neg_data)
    df_neg["label"] = 0

    df = pd.concat([df_pos, df_neg], ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    return df


def train_and_save_model():
    print("Generating training dataset for Threat Persona Attribution...")
    df = generate_training_data(n_samples=3000)

    X = df[FEATURE_NAMES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Training Random Forest Classifier on {len(X_train)} samples...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    # Evaluation
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    roc = roc_auc_score(y_test, probs)
    print("=" * 60)
    print("MODEL EVALUATION RESULTS")
    print("=" * 60)
    print(f"ROC-AUC Score: {roc:.4f}")
    print(classification_report(y_test, preds))

    # Feature importances
    importances = dict(zip(FEATURE_NAMES, [round(float(imp), 4) for imp in model.feature_importances_]))
    print("Feature Importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feat:30} : {imp:.4f}")

    # Save artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model_file = ARTIFACTS_DIR / "rf_final.joblib"
    features_file = ARTIFACTS_DIR / "model_features.json"

    joblib.dump(model, model_file)
    with features_file.open("w", encoding="utf-8") as f:
        json.dump(FEATURE_NAMES, f, indent=2)

    print("=" * 60)
    print(f"Model successfully saved to: {model_file}")
    print(f"Features list saved to:    {features_file}")
    print("=" * 60)
    return model


if __name__ == "__main__":
    train_and_save_model()
