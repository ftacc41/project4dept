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

## Known Issues & Technical Debt

### CRITICAL
1. **`EXPOSE_CONFIG=True` in docker-compose.yml:L86** — Airflow webserver exposes full config (Fernet key, DB creds) at `/config`. Must be set to `"False"` before any non-local deployment.
2. **K8s Fernet key is not read from secret** — `deployment.yaml:L48` injects `{{ .Values.airflow.fernetKey }}` as a plain env var, which defaults to `""`. The comment in `values.yaml` says "set via secretKeyRef" but the template doesn't do this. Fernet key must be wired to a `secretKeyRef` pointing to `airflow-fernet-key`.
3. **RBAC grants write on all secrets/configmaps** (`rbac.yaml:L14-15`) — Airflow service account can create/update/delete any secret in the namespace, including the GCP key and Fernet key. Should be read-only and scoped to specific secret names.
4. **Unsafe pickle deserialization** (`score_churn_model.py:L56`) — `joblib.load(MODEL_PATH)` loads without integrity check. A malicious file on the PVC means arbitrary code execution in the scheduler pod.

### HIGH
5. **Hardcoded default credentials** — Postgres `airflow/airflow`, Airflow `admin/admin`, Grafana `admin/admin` in docker-compose and Helm values. Fine locally; dangerous if the chart is deployed as-is to a real cluster.
6. **Fernet fallback is a broken literal** (`docker-compose.yml:L52`) — `${AIRFLOW_FERNET_KEY:-REDACTED_FERNET_KEY}` is not a valid Fernet key and will crash at runtime if `.env` is missing. Should have no default (fail fast).
7. **Unbounded `SELECT *` will OOM scheduler at scale** — `validate_mart_data.py:L28` and `score_churn_model.py:L37-46` pull full tables into DataFrames with no LIMIT. Will hit the 1.5Gi scheduler memory ceiling as data grows.
8. **No K8s NetworkPolicies** — All pods can reach each other and external endpoints freely. No restriction on inter-pod traffic or egress.

### MEDIUM
9. **`days_ago(1)` is deprecated and non-deterministic** (`marketing_data_extract_load.py:L53`, `marketing_data_ml_scoring.py:L33`) — Recalculates on every scheduler restart. Use a fixed `datetime(2024, 1, 1)` instead.
10. **Null check in `validate_data_files` warns but doesn't gate** (`marketing_data_extract_load.py:L82-83`) — Null values are logged as a warning but the task succeeds. GE catches this later but the inconsistency is misleading.
11. **No `max_value` on `order_amount` GE expectation** (`validate_raw_data.py:L81`) — Only `min_value: 0` is checked; unrealistic values (e.g. $1B) pass silently.
12. **Failure emails point to `admin@example.com`** (`marketing_data_extract_load.py:L39`) — `email_on_failure: True` but the address is a dead end. Either configure SMTP + real address or set to `False`.
13. **Redis is running but unused** (`docker-compose.yml:L21-33`) — LocalExecutor doesn't use Redis. Unnecessary attack surface and memory usage.
14. **Healthcheck ignores HTTP status code** (`Dockerfile:L57`) — `requests.get(...)` succeeds even on `500`. Should use `.raise_for_status()` or hit `/health`.

### LOW
15. **`__import__` pattern in DAG tasks** — Import errors only surface at task runtime, not at DAG parse time. Direct top-level imports would catch errors earlier.
16. **`hostPath` mounts hardcoded to one machine** (`values.yaml:L28-40`) — `/Users/macbook/Desktop/...` paths break for any other developer or CI environment.
17. **`git` installed in runtime image** (`Dockerfile:L26`) — Not used at runtime; adds attack surface and image size.
18. **Unused placeholder DAGs parsed every cycle** — `marketing_data_k8s_executor.py` and `marketing_data_transform.py` are parsed by the scheduler indefinitely. Move to `archive/` outside the DAGs folder.
19. **`np.random.seed(42)` makes every run produce identical data** (`generate_data.py:L25`) — Intentional for demo purposes but means daily runs always overwrite BQ with the same records.
20. **Model metadata silently ignored if missing** (`score_churn_model.py:L81-84`) — If `churn_model_metadata.json` doesn't exist, `model_trained_at` is `None` in predictions with no warning logged.
