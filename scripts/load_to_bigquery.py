"""
Loads CSV files from /tmp/airflow_data into the BigQuery raw dataset.
Uses WRITE_TRUNCATE so each daily run replaces the raw tables cleanly.
"""

from google.cloud import bigquery
from pathlib import Path
import os


PROJECT_ID = "airflow-marketing-analytics"
DATASET = "raw"
DATA_DIR = Path("/tmp/airflow_data")

# Map CSV filename → BQ table name
TABLE_MAP = {
    "customers.csv": "customers",
    "events.csv": "events",
    "orders.csv": "orders",
    "churn_labels.csv": "churn_labels",
}


def load_csv_to_bq(client: bigquery.Client, csv_path: Path, table_id: str) -> None:
    """Load a single CSV file into a BigQuery table (truncate + reload)."""
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    with open(csv_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)

    job.result()  # Wait for completion
    table = client.get_table(table_id)
    print(f"  ✓ {csv_path.name} → {table_id} ({table.num_rows} rows)")


def load_all(**context) -> None:
    """Load all CSVs to BigQuery raw dataset. Called as Airflow PythonOperator."""
    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/home/airflow/.gcp/key.json")
    client = bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)

    print(f"Loading data to BigQuery project={PROJECT_ID} dataset={DATASET}...")

    for filename, table_name in TABLE_MAP.items():
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Expected file not found: {csv_path}")
        table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
        load_csv_to_bq(client, csv_path, table_id)

    print("\n✅ All tables loaded to BigQuery raw layer.")


if __name__ == "__main__":
    load_all()
