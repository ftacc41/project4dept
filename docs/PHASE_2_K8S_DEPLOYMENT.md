# Phase 2: Kubernetes Deployment — Production-Grade Airflow

## 📋 Overview

Phase 2 transforms our LocalExecutor setup into a **production-grade Kubernetes deployment** with the **Kubernetes Executor**. This demonstrates enterprise-level container orchestration and infrastructure-as-code patterns that DEPT® uses in client projects.

**Timeline**: Week 2-3
**Status**: Helm chart complete, ready for deployment

---

## ✅ Phase 2 Deliverables

- [x] Minikube local K8s cluster (4GB RAM, 2 CPUs)
- [x] Helm chart for Airflow with K8s Executor
- [x] RBAC configuration for pod management
- [x] ConfigMaps for Airflow configuration
- [x] Resource limits and health checks
- [x] Deployment script (`deploy-k8s.sh`)
- [ ] Full deployment testing
- [ ] Monitoring setup (Prometheus/Grafana)

---

## 🏗️ Architecture Evolution

### Phase 1: Local Development
```
Docker Compose
├── PostgreSQL (external)
├── Redis (external)
├── Airflow LocalExecutor
└── Single container per service
```

### Phase 2: Production K8s
```
Kubernetes Cluster (Minikube)
├── airflow-project namespace
├── Airflow webserver (Deployment + Service)
├── Airflow scheduler (Deployment)
├── Kubernetes Executor (creates pods per task)
├── RBAC (ServiceAccount + Roles)
└── ConfigMaps (Airflow configuration)
```

---

## 📁 K8s Project Structure

```
k8s/
├── airflow-helm/                    # Helm chart
│   ├── Chart.yaml                   # Chart metadata
│   ├── values.yaml                  # Configuration values
│   ├── templates/
│   │   ├── deployment.yaml          # Webserver + Scheduler deployments
│   │   ├── service.yaml             # Webserver service
│   │   ├── serviceaccount.yaml      # K8s service account
│   │   ├── configmap.yaml           # Airflow configuration
│   │   ├── rbac.yaml                # Roles & bindings for K8s Executor
│   │   └── NOTES.txt                # Post-deployment instructions
│   └── .helmignore
└── .gitkeep
```

---

## ⚓ Helm Chart Features

### Airflow Configuration
- **Executor**: `KubernetesExecutor` (creates pods per task)
- **Namespace**: `airflow-project` (isolated deployment)
- **Resources**: CPU/memory limits for production stability
- **Health Checks**: Liveness/readiness probes

### K8s Executor Benefits
- **Task Isolation**: Each task runs in its own pod
- **Resource Control**: Per-task CPU/memory allocation
- **Scalability**: Horizontal scaling of workers
- **Fault Tolerance**: Pod failures don't affect other tasks

### RBAC Security
- **Service Account**: `airflow-sa` for pod management
- **Role**: Permissions to create/delete pods, jobs, secrets
- **Principle of Least Privilege**: Minimal required permissions

---

## 🚀 Deployment Process

### Prerequisites
```bash
# Install tools
brew install minikube helm

# Start Minikube
minikube start --driver=docker --memory=4096 --cpus=2

# Verify cluster
kubectl get nodes
```

### Deploy with Script
```bash
# Automated deployment
./deploy-k8s.sh
```

### Manual Deployment
```bash
# Build and load image
docker build -t airflow_project-airflow-webserver:latest .
minikube image load airflow_project-airflow-webserver:latest

# Deploy with Helm
helm upgrade --install airflow k8s/airflow-helm \
    --namespace airflow-project \
    --create-namespace \
    --wait

# Port forward
kubectl port-forward -n airflow-project svc/airflow-airflow-helm-webserver 8080:8080
```

---

## 📊 K8s Resources Created

### Deployments
- **airflow-webserver**: Web UI and API (1 replica)
- **airflow-scheduler**: DAG orchestration (1 replica)

### Services
- **airflow-webserver**: ClusterIP service on port 8080

### RBAC
- **ServiceAccount**: `airflow-sa`
- **Role**: Pod/job management permissions
- **RoleBinding**: Links service account to role

### ConfigMaps
- **airflow-config**: Airflow core configuration
  - `AIRFLOW__CORE__EXECUTOR=KubernetesExecutor`
  - `AIRFLOW__KUBERNETES__NAMESPACE=airflow-project`
  - Resource limits and DAG folder paths

---

## 🔧 Configuration Details

### values.yaml Key Settings

```yaml
airflow:
  executor: KubernetesExecutor
  image:
    repository: airflow_project-airflow-webserver
    tag: latest

webserver:
  replicas: 1
  resources:
    requests: {memory: "256Mi", cpu: "250m"}
    limits: {memory: "512Mi", cpu: "500m"}

config:
  airflow__core__dags_folder: "/opt/airflow/dags"
  airflow__kubernetes__namespace: "airflow-project"
  airflow__kubernetes__worker_pods_creation_batch_size: "10"
```

### K8s Executor Behavior
- **Pod Creation**: Each task instance → new pod
- **Resource Allocation**: Configurable per task
- **Cleanup**: Failed pods auto-cleaned
- **Logging**: Pod logs accessible via K8s API

---

## 📈 Scaling & Performance

### Current Setup
- **Webserver**: 256Mi-512Mi RAM, 0.25-0.5 CPU
- **Scheduler**: 256Mi-512Mi RAM, 0.25-0.5 CPU
- **Workers**: 128Mi-256Mi RAM, 0.1-0.2 CPU per pod

### Scaling Options
```bash
# Scale webserver
kubectl scale deployment airflow-webserver --replicas=2 -n airflow-project

# Scale scheduler
kubectl scale deployment airflow-scheduler --replicas=2 -n airflow-project
```

### Resource Monitoring
```bash
# Pod resource usage
kubectl top pods -n airflow-project

# Node resources
kubectl describe nodes
```

---

## 🔍 Debugging & Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n airflow-project
kubectl describe pod <pod-name> -n airflow-project
```

### View Logs
```bash
# Webserver logs
kubectl logs -n airflow-project deployment/airflow-webserver

# Scheduler logs
kubectl logs -n airflow-project deployment/airflow-scheduler

# Task pod logs (K8s Executor)
kubectl logs -n airflow-project <task-pod-name>
```

### Common Issues

**Pods Pending**: Insufficient resources
```bash
kubectl describe pod <pod-name> -n airflow-project
minikube start --memory=6144 --cpus=4  # Increase resources
```

**Image Pull Errors**: Image not loaded
```bash
minikube image load airflow_project-airflow-webserver:latest
```

**RBAC Errors**: Permission denied
```bash
kubectl get rolebindings -n airflow-project
kubectl describe role airflow-airflow-helm-role -n airflow-project
```

---

## 🎯 Interview Talking Points

### K8s Expertise Demonstrated
*"I built a complete Helm chart for Airflow with Kubernetes Executor, implementing RBAC, resource management, and production patterns. This shows I understand enterprise container orchestration."*

### Infrastructure as Code
*"The entire deployment is defined as code - from service accounts to resource limits. This ensures reproducible, version-controlled infrastructure."*

### Production Readiness
*"I configured health checks, resource limits, and proper namespace isolation. The K8s Executor provides task-level isolation and scaling capabilities."*

### Operational Maturity
*"I included monitoring hooks, logging configuration, and deployment automation. This demonstrates how I'd manage Airflow in a production DEPT® environment."*

---

## 📚 Next Steps (Phase 3)

Once K8s deployment is tested:

1. **Deploy to Minikube** and verify DAG execution
2. **Add monitoring** (Prometheus + Grafana)
3. **Configure external database** (connect to docker-compose Postgres)
4. **Test task scaling** with multiple concurrent tasks
5. **Move to Phase 3**: dbt + BigQuery integration

---

## 📄 Files Modified/Created

- `k8s/airflow-helm/Chart.yaml` — Chart metadata
- `k8s/airflow-helm/values.yaml` — Airflow K8s configuration
- `k8s/airflow-helm/templates/deployment.yaml` — Webserver/scheduler deployments
- `k8s/airflow-helm/templates/service.yaml` — Webserver service
- `k8s/airflow-helm/templates/configmap.yaml` — Airflow config
- `k8s/airflow-helm/templates/rbac.yaml` — K8s permissions
- `k8s/airflow-helm/templates/NOTES.txt` — Deployment guide
- `deploy-k8s.sh` — Automated deployment script

---

**Status**: Helm chart complete, templates validated
**Next**: Deploy to Minikube and test K8s Executor functionality
**Date**: 2026-03-18