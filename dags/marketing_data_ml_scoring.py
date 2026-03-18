"""
Phase 4: ML Churn Training DAG

Runs weekly to retrain the XGBoost churn model on the latest
mart_customer_ltv data and saves the artifact to the models PVC.

Decoupled from daily scoring — train weekly, score daily.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import sys

sys.path.insert(0, "/home/airflow/scripts")

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "ml_churn_train",
    default_args=default_args,
    description="Phase 4: Weekly churn model retraining",
    schedule_interval="@weekly",
    start_date=days_ago(1),
    tags=["phase-4", "ml", "train"],
    catchup=False,
)

train_model = PythonOperator(
    task_id="train_churn_model",
    python_callable=lambda **ctx: __import__("train_churn_model", fromlist=[""]).train(**ctx),
    dag=dag,
)
