# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Portfolio project: end-to-end marketing analytics pipeline using Airflow, BigQuery, dbt, and ML (XGBoost). All 5 phases complete.

- **GCP project**: `airflow-marketing-analytics`
- **BigQuery datasets**: `raw`, `staging`, `marts` (US region)
- **GitHub**: `ftacc41/project4dept`

## Development Environments

### Local (Docker Compose)
```bash
docker-compose up -d          # Start all services (Postgres, Redis, Scheduler, Webserver, Init)
docker-compose down           # Stop
docker-compose logs -f        # Follow logs
```
Webserver: http://localhost:8080 (admin/admin)

### Kubernetes (Minikube)
```bash
# CRITICAL: Always build inside Minikube's Docker daemon — `minikube image load` is unreliable
eval $(minikube docker-env)
docker build -t airflow-custom:latest .

# Deploy/upgrade
helm upgrade --install airflow k8s/airflow-helm/ -n airflow-project

# After every image rebuild (latest tag won't re-pull automatically)
kubectl rollout restart deployment airflow-scheduler airflow-webserver -n airflow-project

# Port-forward webserver
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow-project
```

### Monitoring (Phase 6)
Grafana at http://localhost:3000 (admin/admin) and Prometheus at http://localhost:9090 start automatically with `docker-compose up`. The Airflow dashboard is pre-provisioned — no manual setup needed.

For Minikube:
```bash
kubectl port-forward svc/airflow-grafana 3000:3000 -n airflow-project
kubectl port-forward svc/airflow-prometheus 9090:9090 -n airflow-project
```

### dbt (standalone)
```bash
cd dbt/marketing_analytics
# dbt is in an isolated venv to avoid Airflow dependency conflicts
/home/airflow/dbt-venv/bin/dbt run
/home/airflow/dbt-venv/bin/dbt test
/home/airflow/dbt-venv/bin/dbt run --select staging   # Run one layer
```

### gcloud on this machine
```bash
CLOUDSDK_PYTHON=/opt/homebrew/bin/python3.13 gcloud ...
```

## CI/CD (Phase 7)

Workflow at [.github/workflows/ci.yml](.github/workflows/ci.yml):
- **Every push/PR**: DAG syntax check (`py_compile`) + `helm lint`
- **Push to main only**: builds and pushes image to `ghcr.io/ftacc41/project4dept` (`:latest` + `:sha-<short>`)

No secrets needed beyond the automatic `GITHUB_TOKEN`. The pipeline does **not** auto-deploy to Minikube — after a push, run `helm upgrade` manually (see NEXT_STEPS.md).

## DAG Architecture

**DAGs are baked into the Docker image** (not hostPath mounted). Every DAG change requires a full image rebuild and `kubectl rollout restart`. After deploying, wait ~60s before triggering — the scheduler needs time to re-serialize the task graph.

### `marketing_data_extract_load` (daily)
9-task chain:
```
generate_synthetic_data → validate_data_files → summarize_data → dq_validate_raw
  → load_to_bigquery → dbt_run → dbt_test → dq_validate_marts → ml_churn_score
```
- `dq_validate_raw`: Great Expectations validation of 4 raw CSVs (Layer A)
- `dq_validate_marts`: Great Expectations validation of BQ mart tables (Layer C)
- `ml_churn_score`: runs `scripts/score_churn_model.py` against the trained model

### `ml_churn_train` (weekly, file: `marketing_data_ml_scoring.py`)
Single task: trains XGBoost on `marts.mart_customer_ltv`, saves model to PVC at `/home/airflow/models/churn_model.pkl`.

## dbt Project

**Project**: `dbt/marketing_analytics/` | **Profile**: `dbt/profiles.yml`

```
models/
  staging/   → views in `staging` dataset (stg_customers, stg_events, stg_orders, stg_churn_labels)
  marts/     → tables in `marts` dataset (mart_customer_ltv, mart_churn_summary, mart_campaign_performance)
macros/
  generate_schema_name.sql  → prevents `staging_staging` prefix in K8s env; do not remove
```

Schema tests (30 total) in each layer's `schema.yml`. BigQuery auth via service account key at `/home/airflow/.gcp/key.json` (K8s secret `airflow-gcp-key`).

**Key data facts**:
- `mart_campaign_performance` grain: `(campaign_id, channel)`, not `campaign_id` alone
- `net_ltv` can be negative (acquisition cost can exceed revenue)

## Infrastructure Notes

- **Scheduler memory**: set to 1.5Gi in Helm values — 1Gi causes OOMKills during concurrent dbt + BQ load
- **Fernet key**: stored in K8s secret `airflow-fernet-key` (rotated after a GitGuardian alert — never commit it)
- **Service account key**: `~/.config/gcloud/airflow-dbt-sa-key.json` locally; mounted as K8s secret in cluster
- **GE (Great Expectations)**: uses `EphemeralDataContext` — no filesystem setup needed
- **dbt venv**: `/home/airflow/dbt-venv` isolated from Airflow's Python env; `DBT_BIN` env var points to it
