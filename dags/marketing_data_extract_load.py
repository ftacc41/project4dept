"""
Phase 1 + 3: Extract, Load, and Transform DAG
Generates synthetic marketing data, loads it to BigQuery raw layer,
then triggers dbt to build staging views and mart tables.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, "/home/airflow/scripts")


# Default DAG arguments
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['admin@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'marketing_data_extract_load',
    default_args=default_args,
    description='Phase 1: Extract and load synthetic marketing data',
    schedule_interval='@daily',  # Run daily
    start_date=days_ago(1),
    tags=['phase-1', 'extract', 'load'],
    catchup=False,
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
        
        if df.isnull().sum().sum() > 0:
            print(f"    ⚠ Warning: Found {df.isnull().sum().sum()} null values")


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

# Task 4: Load CSVs to BigQuery raw layer
load_to_bq = PythonOperator(
    task_id='load_to_bigquery',
    python_callable=lambda **ctx: __import__('load_to_bigquery', fromlist=['']).load_all(**ctx),
    dag=dag,
)

# Task 5: Run dbt models (staging views + mart tables)
dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='cd /home/airflow/dbt/marketing_analytics && dbt run --profiles-dir /home/airflow/.dbt',
    dag=dag,
)

# Task 6: Run dbt tests
dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='cd /home/airflow/dbt/marketing_analytics && dbt test --profiles-dir /home/airflow/.dbt',
    dag=dag,
)

# Define task dependencies
generate_data >> validate_files >> summarize_data_task >> load_to_bq >> dbt_run >> dbt_test
