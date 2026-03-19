"""
Phase 1 + 3 + 6: Extract, Load, Transform, and Monitor DAG
Generates synthetic marketing data, loads it to BigQuery raw layer,
triggers dbt to build staging views and mart tables, then scores the churn model.
SLA is set to 2 hours; misses are logged and emitted as StatsD metrics.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import pandas as pd
from pathlib import Path
import sys
import logging

sys.path.insert(0, "/home/airflow/scripts")

log = logging.getLogger(__name__)


def sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):
    """Log SLA misses; Airflow also auto-emits airflow.sla_miss to StatsD."""
    missed = ", ".join(str(sla.task_id) for sla in slas)
    log.warning(
        "SLA MISS on DAG '%s' — tasks: [%s]. "
        "Blocking tasks: %s",
        dag.dag_id,
        missed,
        ", ".join(str(ti.task_id) for ti in blocking_tis),
    )


# Default DAG arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email_on_failure': False,  # no SMTP configured; set to True and add 'email' once SMTP is set up
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'sla': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    'marketing_data_extract_load',
    default_args=default_args,
    description='Phase 1 + 6: Extract, load, transform, and monitor marketing data',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    tags=['phase-1', 'extract', 'load', 'monitoring'],
    catchup=False,
    sla_miss_callback=sla_miss_callback,
)


def validate_data_files(**context):
    """
    Validate that all expected data files were generated.
    """
    data_dir = Path('/tmp/airflow_data')
    required_files = ['customers.csv', 'events.csv', 'orders.csv', 'churn_labels.csv']
    
    print(f"Validating data files in {data_dir}...")
    
    for file in required_files:
        file_path = data_dir / file
        if not file_path.exists():
            raise FileNotFoundError(f"Missing file: {file}")
        
        # Check file size
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ {file} ({size_mb:.2f} MB)")
        
        # Basic data quality check
        df = pd.read_csv(file_path)
        print(f"    - {len(df)} rows, {len(df.columns)} columns")
        
        null_count = df.isnull().sum().sum()
        if null_count > 0:
            raise ValueError(
                f"{file}: found {null_count} null values across {df.isnull().any(axis=1).sum()} rows"
            )


def summarize_data(**context):
    """
    Print summary statistics about generated data.
    """
    data_dir = Path('/tmp/airflow_data')
    
    print("\n📊 Data Summary:")
    print("-" * 50)
    
    customers_df = pd.read_csv(data_dir / 'customers.csv')
    events_df = pd.read_csv(data_dir / 'events.csv')
    orders_df = pd.read_csv(data_dir / 'orders.csv')
    churn_df = pd.read_csv(data_dir / 'churn_labels.csv')
    
    print(f"Customers: {len(customers_df)}")
    print(f"  - Segments: {customers_df['segment'].value_counts().to_dict()}")
    print(f"  - Regions: {customers_df['region'].value_counts().to_dict()}")
    
    print(f"\nEvents: {len(events_df)}")
    print(f"  - Types: {events_df['event_type'].value_counts().to_dict()}")
    print(f"  - Date range: {events_df['event_timestamp'].min()} to {events_df['event_timestamp'].max()}")
    
    print(f"\nOrders: {len(orders_df)}")
    print(f"  - Total value: ${orders_df['order_amount'].sum():,.2f}")
    print(f"  - Average order: ${orders_df['order_amount'].mean():,.2f}")
    print(f"  - Status: {orders_df['status'].value_counts().to_dict()}")
    
    print(f"\nChurn: {(churn_df['is_churned'] == 1).sum()} churned customers ({(churn_df['is_churned'].mean() * 100):.1f}%)")
    print("-" * 50)


# Task 1: Generate synthetic data
generate_data = BashOperator(
    task_id='generate_synthetic_data',
    bash_command='cd /home/airflow && python scripts/generate_data.py',
    dag=dag,
)

# Task 2: Validate generated files
validate_files = PythonOperator(
    task_id='validate_data_files',
    python_callable=validate_data_files,
    dag=dag,
)

# Task 3: Summarize data
summarize_data_task = PythonOperator(
    task_id='summarize_data',
    python_callable=summarize_data,
    dag=dag,
)

# Task 4: GE Layer A — validate raw CSVs before loading to BigQuery
dq_validate_raw = PythonOperator(
    task_id='dq_validate_raw',
    python_callable=lambda **ctx: __import__('validate_raw_data', fromlist=['']).validate(**ctx),
    dag=dag,
)

# Task 5: Load CSVs to BigQuery raw layer
load_to_bq = PythonOperator(
    task_id='load_to_bigquery',
    python_callable=lambda **ctx: __import__('load_to_bigquery', fromlist=['']).load_all(**ctx),
    dag=dag,
)

# Task 6: Run dbt models (staging views + mart tables)
dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='cd /home/airflow/dbt/marketing_analytics && /home/airflow/dbt-venv/bin/dbt run --profiles-dir /home/airflow/.dbt',
    dag=dag,
)

# Task 7: Run dbt tests
dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='cd /home/airflow/dbt/marketing_analytics && /home/airflow/dbt-venv/bin/dbt test --profiles-dir /home/airflow/.dbt',
    dag=dag,
)

# Task 8: GE Layer C — validate mart tables after dbt runs
dq_validate_marts = PythonOperator(
    task_id='dq_validate_marts',
    python_callable=lambda **ctx: __import__('validate_mart_data', fromlist=['']).validate_marts(**ctx),
    dag=dag,
)

# Task 9: Score customers using trained churn model → writes to marts.ml_churn_predictions
ml_score = PythonOperator(
    task_id='ml_churn_score',
    python_callable=lambda **ctx: __import__('score_churn_model', fromlist=['']).score(**ctx),
    dag=dag,
)

# Define task dependencies
generate_data >> validate_files >> summarize_data_task >> dq_validate_raw >> load_to_bq >> dbt_run >> dbt_test >> dq_validate_marts >> ml_score
