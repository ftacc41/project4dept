"""
Loads the trained churn model from /home/airflow/models/ and scores all
customers in mart_customer_ltv, writing predictions to marts.ml_churn_predictions.

Run daily via the marketing_data_extract_load DAG after dbt_test.
"""

import os
import json
import hashlib
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime

from google.cloud import bigquery


PROJECT_ID = "airflow-marketing-analytics"
MODEL_PATH = Path("/home/airflow/models/churn_model.pkl")
METADATA_PATH = Path("/home/airflow/models/churn_model_metadata.json")

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


def fetch_customers(client: bigquery.Client) -> pd.DataFrame:
    """Pull all customers from mart_customer_ltv for scoring."""
    query = f"""
        SELECT
            customer_id,
            name,
            segment,
            region,
            {", ".join(NUMERIC_FEATURES)}
        FROM `{PROJECT_ID}.marts.mart_customer_ltv`
    """
    return client.query(query).to_dataframe()


def score(**context) -> None:
    """Load model, score customers, write predictions to BQ."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No model found at {MODEL_PATH}. Run the ml_churn_train DAG first."
        )

    # Verify SHA-256 checksum before deserializing to guard against tampered model files
    checksum_path = MODEL_PATH.with_suffix(".pkl.sha256")
    if not checksum_path.exists():
        raise FileNotFoundError(
            f"No checksum file found at {checksum_path}. Retrain the model to generate one."
        )
    expected = checksum_path.read_text().strip()
    actual = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(
            f"Model checksum mismatch — file may have been tampered with.\n"
            f"  Expected: {expected}\n  Got:      {actual}"
        )
    print(f"  ✓ Model checksum verified ({actual[:16]}...)")

    artifact = joblib.load(MODEL_PATH)
    model = artifact["model"]
    encoders = artifact["encoders"]

    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/home/airflow/.gcp/key.json")
    client = bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

    print("Fetching customers from BigQuery...")
    df = fetch_customers(client)
    print(f"  Scoring {len(df)} customers")

    # Apply same encoding used during training
    for col, le in encoders.items():
        # Handle unseen categories gracefully
        df[col] = df[col].astype(str).map(
            lambda x, le=le: le.transform([x])[0] if x in le.classes_ else -1
        )

    X = df[ALL_FEATURES]
    df["churn_probability"] = model.predict_proba(X)[:, 1].round(4)
    df["churn_prediction"] = (df["churn_probability"] >= 0.5).astype(bool)
    df["scored_at"] = datetime.utcnow().isoformat()

    # Load model metadata for traceability
    model_trained_at = None
    if METADATA_PATH.exists():
        meta = json.loads(METADATA_PATH.read_text())
        model_trained_at = meta.get("trained_at")
    df["model_trained_at"] = model_trained_at

    output = df[["customer_id", "churn_probability", "churn_prediction", "scored_at", "model_trained_at"]]

    # Write to BQ (truncate + reload)
    table_id = f"{PROJECT_ID}.marts.ml_churn_predictions"
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    job = client.load_table_from_dataframe(output, table_id, job_config=job_config)
    job.result()

    churned = df["churn_prediction"].sum()
    print(f"\n✅ Scored {len(df)} customers → {table_id}")
    print(f"   Predicted churned: {churned} ({churned/len(df):.1%})")
    print(f"   Avg churn probability: {df['churn_probability'].mean():.3f}")


if __name__ == "__main__":
    score()
