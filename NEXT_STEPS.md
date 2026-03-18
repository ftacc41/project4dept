# Next Steps (Resume Checklist)

## ✅ Completed
- [x] Phase 1: Local Airflow + Docker (completed)
- [x] Phase 2: Helm chart created and deployed to Minikube (LocalExecutor + in-cluster Postgres)
- [x] Phase 3: BigQuery + dbt integration (completed)

## Phase 3 — What was built

### Infrastructure
- GCP project: `airflow-marketing-analytics`
- BQ datasets: `raw`, `staging`, `marts` (US region)
- Service account: `airflow-dbt-sa` — key stored as K8s secret `airflow-gcp-key`
- dbt installed in isolated venv at `/home/airflow/dbt-venv` (avoids Airflow dep conflicts)

### dbt project: `dbt/marketing_analytics/`
- **Staging views** (in `staging` dataset): stg_customers, stg_orders, stg_events, stg_churn_labels
- **Mart tables** (in `marts` dataset): mart_customer_ltv, mart_churn_summary, mart_campaign_performance
- 30 schema tests, all passing

### DAG: `marketing_data_extract_load`
generate_synthetic_data → validate_data_files → summarize_data → load_to_bigquery → dbt_run → dbt_test

## 🔜 Next: Phase 4 — ML Scoring

Options:
1. Train a churn model on `mart_customer_ltv` data (scikit-learn / XGBoost)
2. Score customers and write predictions back to BQ (`marts.ml_churn_predictions`)
3. Add `ml_score` task to the DAG after `dbt_test`
4. Optionally retrain on schedule vs. score-only each run

## Key debugging notes (for context)
- Scheduler needs 1Gi memory limit (512Mi OOMKills when forking LocalExecutor tasks)
- dbt first-run BQ auth takes ~20s before output — Airflow retry handles this
- `mart_campaign_performance` grain is (campaign_id, channel), not campaign_id alone
- `gcloud` needs `CLOUDSDK_PYTHON=/opt/homebrew/bin/python3.13` on this machine
