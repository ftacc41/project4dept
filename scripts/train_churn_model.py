"""
Trains an XGBoost churn classifier on mart_customer_ltv data from BigQuery.
Saves the model artifact and feature metadata to /home/airflow/models/.

Run weekly via the ml_churn_train DAG.
"""

import os
import json
import hashlib
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

from google.cloud import bigquery
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report
from xgboost import XGBClassifier


PROJECT_ID = "airflow-marketing-analytics"
MODEL_DIR = Path("/home/airflow/models")
MODEL_PATH = MODEL_DIR / "churn_model.pkl"
METADATA_PATH = MODEL_DIR / "churn_model_metadata.json"

NUMERIC_FEATURES = [
    "total_orders",
    "total_revenue",
    "avg_order_value",
    "customer_lifespan_days",
    "net_ltv",
    "age",
    "acquisition_cost",
]
CATEGORICAL_FEATURES = ["segment", "region"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "is_churned"


def fetch_training_data(client: bigquery.Client) -> pd.DataFrame:
    """Pull labeled customer data from mart_customer_ltv."""
    query = f"""
        SELECT
            {", ".join(ALL_FEATURES)},
            {TARGET}
        FROM `{PROJECT_ID}.marts.mart_customer_ltv`
        WHERE {TARGET} IS NOT NULL
    """
    return client.query(query).to_dataframe()


def encode_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Label-encode categorical features and return encoders for scoring."""
    encoders = {}
    for col in CATEGORICAL_FEATURES:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    return df, encoders


def train(**context) -> None:
    """Train XGBoost churn model, evaluate, and save artifact to model dir."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/home/airflow/.gcp/key.json")
    client = bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

    print("Fetching training data from BigQuery...")
    df = fetch_training_data(client)
    print(f"  {len(df)} rows, churn rate: {df[TARGET].mean():.1%}")

    df, encoders = encode_features(df)

    X = df[ALL_FEATURES]
    y = df[TARGET].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Class weight to handle imbalance
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print(f"\nModel AUC: {auc:.4f}")
    print(classification_report(y_test, model.predict(X_test), target_names=["active", "churned"]))

    # Save model + encoders together
    artifact = {"model": model, "encoders": encoders, "features": ALL_FEATURES}
    joblib.dump(artifact, MODEL_PATH)
    print(f"\n✅ Model saved to {MODEL_PATH}")

    # Write SHA-256 checksum so score_churn_model.py can verify integrity before loading
    checksum = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    (MODEL_DIR / "churn_model.pkl.sha256").write_text(checksum)
    print(f"✅ Checksum written: {checksum[:16]}...")

    # Save metadata for audit trail
    metadata = {
        "trained_at": datetime.utcnow().isoformat(),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "auc": round(auc, 4),
        "churn_rate": round(float(y.mean()), 4),
        "features": ALL_FEATURES,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))
    print(f"✅ Metadata saved to {METADATA_PATH}")


if __name__ == "__main__":
    train()
