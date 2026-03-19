# Next Steps (Resume Checklist)

## ✅ Completed

- [x] Phase 1: Synthetic data generation + local Airflow + Docker
- [x] Phase 2: Helm chart deployed to Minikube (LocalExecutor + in-cluster Postgres)
- [x] Phase 3: BigQuery + dbt integration
- [x] Phase 4: ML churn model (XGBoost, train/score decoupled)
- [x] Phase 5: Great Expectations data quality (Layer A + Layer C)
- [x] Phase 6: Monitoring (Prometheus + Grafana via StatsD exporter)

---

## Infrastructure Summary

- **GCP project**: `airflow-marketing-analytics`
- **BQ datasets**: `raw`, `staging`, `marts` (US region)
- **Service account**: `airflow-dbt-sa` — key stored as K8s secret `airflow-gcp-key`
- **K8s namespace**: `airflow-project` (Minikube, docker driver)
- **Helm release**: `airflow` — `helm upgrade airflow k8s/airflow-helm/ -n airflow-project`
- **dbt venv**: `/home/airflow/dbt-venv` (isolated to avoid Airflow dep conflicts)
- **ML model**: XGBoost at `/home/airflow/models/churn_model.pkl` on PVC `ml-models-pvc`
- **Fernet key**: stored in K8s secret `airflow-fernet-key` (rotated after GitGuardian alert)
- **GitHub**: `ftacc41/project4dept`

---

## Current DAG: `marketing_data_extract_load` (daily)

```
generate_synthetic_data
  → validate_data_files
  → summarize_data
  → dq_validate_raw          ← GE Layer A: validates 4 raw CSVs
  → load_to_bigquery
  → dbt_run
  → dbt_test
  → dq_validate_marts        ← GE Layer C: validates mart tables in BQ
  → ml_churn_score
```

## DAG: `marketing_data_ml_scoring` (weekly)
```
train_churn_model            ← trains XGBoost on mart_customer_ltv, saves to PVC
```

---

## dbt project: `dbt/marketing_analytics/`

- **Staging views** (`staging` dataset): stg_customers, stg_orders, stg_events, stg_churn_labels
- **Mart tables** (`marts` dataset): mart_customer_ltv, mart_churn_summary, mart_campaign_performance
- **ML output** (`marts` dataset): ml_churn_predictions (written by score_churn_model.py)
- Schema: `generate_schema_name` macro ensures correct dataset routing (no `staging_staging` prefix)
- 30 schema tests, all passing

---

## Key debugging notes

- Always build image inside Minikube daemon: `eval $(minikube docker-env) && docker build ...`
- Always `kubectl rollout restart` after rebuild — `latest` tag won't pull otherwise
- Scheduler needs 1.5Gi memory (1Gi OOMKills during dbt + BQ load concurrency)
- `mart_campaign_performance` grain is (campaign_id, channel), not campaign_id alone
- `net_ltv` can be legitimately negative (high acquisition cost vs. low revenue)
- GE EphemeralDataContext used — no filesystem setup needed in containers
- `gcloud` needs `CLOUDSDK_PYTHON=/opt/homebrew/bin/python3.13` on this machine

---

## 🔧 Pending actions

- [ ] Update any config or `.env` references to the service account key — path changed to `~/.config/gcloud/airflow-dbt-sa-key.json` (moved from home root on 2026-03-19)

---

## Phase 6 Infrastructure

- **StatsD exporter**: `prom/statsd-exporter:v0.26.0` — receives Airflow metrics on UDP 8125, exposes Prometheus /metrics on port 9102
- **Prometheus**: `prom/prometheus:v2.51.0` — scrapes statsd-exporter every 15s, 7-day retention
- **Grafana**: `grafana/grafana:10.4.0` — port 3000 (admin/admin), auto-provisioned datasource + dashboard
- **Mapping config**: `monitoring/statsd-exporter-mapping.yml` — extracts dag_id, operator, pool as Prometheus labels
- **Dashboard**: `monitoring/grafana/dashboards/airflow.json` — 8 panels: scheduler health, SLA misses, task success/failure, DAG run duration, schedule delay, pool slots
- **SLA**: 2-hour SLA on `marketing_data_extract_load`; misses logged + emitted as `airflow.sla_miss` StatsD metric
- **K8s**: `k8s/airflow-helm/templates/monitoring.yaml` — deploys all 3 services; dashboard JSON loaded via `k8s/airflow-helm/files/airflow-dashboard.json`

### Monitoring quick start
```bash
# Docker Compose
docker-compose up -d
# Grafana: http://localhost:3000  Prometheus: http://localhost:9090

# Minikube — after helm upgrade
kubectl port-forward svc/airflow-grafana 3000:3000 -n airflow-project
kubectl port-forward svc/airflow-prometheus 9090:9090 -n airflow-project
```

## 🔜 Potential next phases

- **Phase 7**: CI/CD (GitHub Actions: rebuild image + redeploy on push to main)
- **Viz**: Looker Studio or Metabase dashboard on mart tables
- **Wrap-up**: README polish, architecture diagram
