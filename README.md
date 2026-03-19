# Marketing Analytics Platform

An end-to-end data engineering pipeline built with Airflow, dbt, BigQuery, Kubernetes, and ML — covering orchestration, transformation, data quality, machine learning, monitoring, and CI/CD.

---

## What It Does

Ingests synthetic marketing data (customers, orders, GA4-style events) through a fully automated daily pipeline that cleans, transforms, and models the data in BigQuery, trains a churn prediction model weekly, and exposes pipeline health metrics in Grafana.

**Pipeline (daily):**
```
generate_data → validate_files → summarize → GE Layer A
  → load_to_bigquery → dbt run → dbt test → GE Layer C → churn_score
```

**ML retraining (weekly):** XGBoost trained on `mart_customer_ltv`, saved to a persistent volume, scored daily against the full customer base.

---

## Stack

| Layer | Tool |
|---|---|
| Orchestration | Apache Airflow 2.8 (LocalExecutor) |
| Containerization | Docker (multi-stage build) |
| Kubernetes | Minikube + Helm |
| Data Warehouse | BigQuery (GCP) |
| Transformation | dbt (staging views + mart tables) |
| Data Quality | Great Expectations + dbt schema tests |
| ML | XGBoost, scikit-learn |
| Monitoring | Prometheus + Grafana (StatsD exporter) |
| CI/CD | GitHub Actions + GHCR |

---

## Architecture

```
Synthetic Data (CSV)
        │
        ▼
  Airflow DAG (daily)
        │
        ├── Great Expectations (Layer A) — validates raw CSVs
        │
        ├── BigQuery raw dataset
        │
        ├── dbt
        │     ├── staging/  (views)   — stg_customers, stg_orders, stg_events, stg_churn_labels
        │     └── marts/    (tables)  — mart_customer_ltv, mart_churn_summary, mart_campaign_performance
        │
        ├── Great Expectations (Layer C) — validates mart tables
        │
        └── Churn scoring → marts.ml_churn_predictions

  Airflow DAG (weekly)
        └── XGBoost training → /models/churn_model.pkl (PVC)

  Metrics
        └── Airflow StatsD → statsd-exporter → Prometheus → Grafana
```

---

## Quick Start (Docker Compose)

**Prerequisites:** Docker Desktop, 4GB+ RAM

```bash
git clone https://github.com/ftacc41/project4dept.git
cd project4dept

cp .env.example .env
# Fill in AIRFLOW_FERNET_KEY and BigQuery credentials

docker-compose up -d
```

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

---

## Kubernetes Deployment (Minikube)

```bash
# Build image inside Minikube's Docker daemon
eval $(minikube docker-env)
docker build -t airflow-custom:latest .

# Deploy
helm upgrade --install airflow k8s/airflow-helm/ -n airflow-project

# Access
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow-project
kubectl port-forward svc/airflow-grafana 3000:3000 -n airflow-project
```

---

## dbt Models

**Staging** (`staging` dataset — views, built from raw BigQuery tables):

| Model | Description |
|---|---|
| `stg_customers` | Cleaned customer master with segment and region |
| `stg_orders` | Cleaned orders with status normalization |
| `stg_events` | GA4-style events with timestamp parsing |
| `stg_churn_labels` | Labeled churn outcomes for ML |

**Marts** (`marts` dataset — tables, analytics-ready):

| Model | Description |
|---|---|
| `mart_customer_ltv` | Customer LTV, order history, churn label — primary ML input |
| `mart_churn_summary` | Churn rates aggregated by segment and region |
| `mart_campaign_performance` | Campaign ROI by campaign and channel |

30 schema tests across both layers covering uniqueness, nullability, and referential integrity.

---

## Data Quality

Two Great Expectations validation layers baked into the daily DAG:

- **Layer A** (pre-load): validates row counts, nulls, and data types on raw CSVs before they touch BigQuery
- **Layer C** (post-transform): validates mart tables for freshness, key cardinality, and expected value ranges after dbt runs

Uses `EphemeralDataContext` — no filesystem setup required in containers.

---

## ML Pipeline

- **Training** (weekly DAG): reads `mart_customer_ltv` from BigQuery, engineers features, trains XGBoost classifier, writes model + metadata to a Kubernetes PVC (`ml-models-pvc`)
- **Scoring** (daily DAG, final task): loads the persisted model, scores all customers, writes predictions to `marts.ml_churn_predictions`
- Decoupled train/score so a broken training run doesn't block daily scoring

---

## Monitoring

Airflow emits StatsD metrics natively. The monitoring stack translates and visualizes them:

```
Airflow → StatsD (UDP 8125) → statsd-exporter → Prometheus → Grafana
```

Pre-provisioned Grafana dashboard covers: scheduler heartbeat, SLA misses, task success/failure rates, DAG run duration, schedule delay, and pool slot usage.

SLA on the daily DAG is set to 2 hours. Misses are logged and surface as `airflow_sla_miss_total` in Prometheus.

---

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):

- **On every push and PR:** DAG syntax check (`py_compile`) + `helm lint`
- **On push to main:** builds Docker image, pushes to `ghcr.io/ftacc41/project4dept` with `latest` and `sha-<commit>` tags

Uses GitHub's built-in `GITHUB_TOKEN` — no extra secrets required. Build layer caching via GitHub Actions cache.

---

## Project Structure

```
├── dags/
│   ├── marketing_data_extract_load.py   # Daily 9-task pipeline
│   └── marketing_data_ml_scoring.py     # Weekly XGBoost training
├── dbt/
│   └── marketing_analytics/
│       ├── models/staging/              # 4 staging views
│       ├── models/marts/                # 3 mart tables
│       └── macros/                      # Schema routing macro
├── scripts/
│   ├── generate_data.py                 # Synthetic data generation
│   ├── load_to_bigquery.py              # CSV → BigQuery raw
│   ├── train_churn_model.py             # XGBoost training
│   ├── score_churn_model.py             # Batch scoring
│   ├── validate_raw_data.py             # GE Layer A
│   └── validate_mart_data.py            # GE Layer C
├── k8s/airflow-helm/                    # Helm chart (Airflow + monitoring)
├── monitoring/                          # Prometheus, Grafana, StatsD config
├── .github/workflows/ci.yml             # GitHub Actions CI/CD
├── Dockerfile                           # Multi-stage Airflow image
└── docker-compose.yml                   # Local dev (8 services)
```

---

## GCP Setup

- **Project**: `airflow-marketing-analytics`
- **Datasets**: `raw`, `staging`, `marts` (US region)
- **Auth**: service account key mounted as K8s secret (`airflow-gcp-key`) or local `.env`
