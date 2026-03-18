# Next Steps (Resume Checklist)

This file is a quick reference to pick up development where you left off.

## ✅ Completed
- [x] Phase 1: Local Airflow + Docker (completed)
- [x] Phase 2: Helm chart created and templated (validated)

## ▶️ Next: Verify Webserver is Healthy (Phase 2 Validation)

Helm install succeeded. Postgres ✅ Scheduler ✅ Webserver was starting when session ended.

1. Check pod status:
   ```bash
   kubectl get pods -n airflow-project
   ```
2. If webserver is still crashing, check logs:
   ```bash
   kubectl logs -n airflow-project deployment/airflow-airflow-helm-webserver
   ```
3. Once webserver is `Running` + `READY 1/1`, port-forward:
   ```bash
   kubectl port-forward -n airflow-project svc/airflow-airflow-helm-webserver 8080:8080
   ```
4. Open http://localhost:8080 — admin / admin

## ✅ After Deployment (Validation)
- [ ] Confirm all 3 pods Running (postgres, scheduler, webserver)
- [ ] Trigger `marketing_data_extract_load` DAG from UI
- [ ] Confirm tasks complete successfully
- [ ] Confirm data files appear in `/tmp/airflow_data/` inside container

### Key fixes made this session (context for debugging)
- Switched `KubernetesExecutor` → `LocalExecutor` (K8s executor needs shared PVC/git-sync, too complex for local demo)
- Added in-cluster Postgres (`k8s/airflow-helm/templates/postgres.yaml`)
- Replaced `hostPath` volumes with `emptyDir` (Minikube Docker driver can't access Mac filesystem)
- Fixed DAGs path: `/home/airflow/airflow/dags` (matches `AIRFLOW_HOME` in Dockerfile)
- Added `db-init` init container (runs `airflow db init` + creates admin user)
- Reduced gunicorn workers to 1, timeout to 300s (gunicorn was timing out on limited Minikube resources)
- Bumped webserver memory limit to 1Gi

## 🔜 Next Major Phase (Phase 3)
- Setup BigQuery (or DuckDB) and dbt
- Create dbt models + schema tests
- Add dbt run to Airflow DAG
