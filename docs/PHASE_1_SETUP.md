# Marketing Analytics Platform — Phase 1: Foundation & Local Airflow

## 📋 Overview

Phase 1 sets up a working Airflow environment locally using Docker, with a basic data extraction pipeline that generates synthetic marketing data.

**Timeline**: Week 1-2  
**Status**: In Progress

---

## ✅ Phase 1 Deliverables

- [x] Project directory structure
- [x] Dockerfile with multi-stage build
- [x] docker-compose.yml (Postgres + Redis + Airflow)
- [x] requirements.txt (dependencies)
- [x] Synthetic data generator script
- [x] First DAG: extract → validate → summarize
- [ ] Local testing (Airflow UI accessible)
- [ ] Documentation complete

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- ~4GB free disk space
- macOS/Linux terminal

### Setup

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```

2. **Start Airflow**
   ```bash
   docker-compose up -d
   ```

   This will:
   - Initialize PostgreSQL database
   - Build custom Airflow image
   - Start scheduler, webserver, and support services
   - Initialize admin user (admin/admin)

3. **Access Airflow UI**
   - Open http://localhost:8080
   - Login: `admin` / `admin`

4. **Trigger DAG**
   - Find `marketing_data_extract_load` in DAG list
   - Click "Trigger DAG" button
   - Watch execution in Airflow UI

### Logs & Debugging

```bash
# View all containers
docker ps

# View logs
docker-compose logs -f airflow-scheduler
docker-compose logs -f airflow-webserver

# Execute command in container
docker-compose exec airflow-webserver bash

# Stop all services
docker-compose down

# Clean up volumes (WARNING: deletes data)
docker-compose down -v
```

---

## 📁 Project Structure

```
airflow_project/
├── dags/
│   └── marketing_data_extract_load.py    # Phase 1 DAG
├── plugins/                              # Custom Airflow plugins (future)
├── scripts/
│   └── generate_data.py                  # Synthetic data generator
├── dbt/                                  # dbt project (Phase 3)
├── k8s/                                  # Kubernetes configs (Phase 2)
├── docs/                                 # Documentation
├── tests/                                # Tests
├── docker-compose.yml                    # Local dev orchestration
├── Dockerfile                            # Custom Airflow image
├── requirements.txt                      # Python dependencies
├── .env.example                          # Environment template
└── .gitignore
```

---

## 🏗️ Architecture (Phase 1)

```
┌─────────────────────────────────────────────┐
│         Airflow Orchestration               │
├─────────────────────────────────────────────┤
│                                             │
│  Task 1: Generate Synthetic Data            │
│    └─> /tmp/airflow_data/                   │
│        - customers.csv (1K rows)            │
│        - events.csv (50K rows)              │
│        - orders.csv (~5K rows)              │
│        - churn_labels.csv (1K rows)         │
│                                             │
│  Task 2: Validate Files                     │
│    └─> Check existence, size, schema       │
│                                             │
│  Task 3: Summarize Data                     │
│    └─> Print statistics & quality metrics   │
│                                             │
└─────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│       PostgreSQL (Airflow Metadata)         │
│   - DAG runs, task states, logs             │
└─────────────────────────────────────────────┘
```

---

## 📊 Generated Data Schema

### customers.csv
```
customer_id, acquisition_date, region, segment, created_at
1, 2023-01-15, US, Premium, 2024-03-17 12:00:00
...
```

### events.csv (GA4-like)
```
event_id, customer_id, event_type, event_timestamp, event_value, page_url, device_type, country, created_at
evt_00000001, 123, page_view, 2024-03-17 10:30:00, 0, https://example.com/page_1, mobile, US, 2024-03-17 12:00:00
...
```

Event types: `page_view`, `click`, `add_to_cart`, `purchase`, `wishlist`, `review`

### orders.csv
```
order_id, customer_id, order_date, order_amount, source, status, created_at
1, 123, 2024-03-17 10:35:00, 156.42, organic, completed, 2024-03-17 12:00:00
...
```

### churn_labels.csv (for ML training)
```
customer_id, is_churned, label_date
123, 0, 2024-03-17
124, 1, 2024-03-17
...
```

---

## 🔧 Configuration

### Airflow Settings (docker-compose.yml)
- **Executor**: LocalExecutor (single machine, scaling via K8s in Phase 2)
- **Backend**: PostgreSQL (production-grade)
- **Broker**: Redis (for future Celery scaling)
- **DAG Load Interval**: 300 seconds

### Data Generation (scripts/generate_data.py)
- **Customers**: 1,000 (configurable)
- **Events**: 50,000 (configurable)
- **Time Window**: Last 90 days
- **Realistic Distribution**: RFM patterns, seasonal trends

---

## 📝 DAG Breakdown: `marketing_data_extract_load`

### Task 1: `generate_synthetic_data`
- Operator: BashOperator
- Runs: `python scripts/generate_data.py`
- Output: CSV files in `/tmp/airflow_data/`
- Purpose: Bootstrap pipeline with realistic data

### Task 2: `validate_data_files`
- Operator: PythonOperator
- Checks: File existence, size, row counts
- Raises: Exception if validation fails
- Purpose: Data quality gate

### Task 3: `summarize_data`
- Operator: PythonOperator
- Prints: Statistics by segment, event type, churn rate
- Purpose: Logging & visibility

### DAG Dependencies
```
generate_synthetic_data
    ↓
validate_data_files
    ↓
summarize_data
```

---

## 🧪 Testing DAG Locally (Without Docker)

```bash
# Install dependencies locally
pip install -r requirements.txt

# Test DAG syntax
python -c "from dags.marketing_data_extract_load import dag; print(dag)"

# Run task directly
python scripts/generate_data.py
```

---

## 🚨 Troubleshooting

### Port 8080 already in use
```bash
lsof -i :8080  # Find process
kill -9 <PID>  # Kill it
```

### PostgreSQL connection error
```bash
docker-compose logs postgres
# Wait 30s for postgres to fully start, then restart scheduler
```

### DAG not appearing in UI
```bash
# Check DAG folder is mounted
docker-compose exec airflow-scheduler ls -la /home/airflow/airflow/dags/

# Wait 5 minutes (DAG parse interval is 300s)
```

### Out of disk space
```bash
docker system prune -a  # Remove unused images
docker-compose down -v  # Remove volumes
```

---

## 📈 Next Steps (Phase 2)

- Convert LocalExecutor → **Kubernetes Executor**
- Add Minikube for local K8s testing
- Deploy Airflow to Minikube with Helm
- Add monitoring & logging

---

## 📚 Resources

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)

---

**Last Updated**: 2026-03-17  
**Maintained By**: Data Engineering Team
