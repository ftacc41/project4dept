#!/bin/bash
# Deploy Airflow to Kubernetes with Helm

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELM_CHART_DIR="$PROJECT_DIR/k8s/airflow-helm"
NAMESPACE="airflow-project"

echo "🚀 Deploying Airflow to Kubernetes"
echo "=================================="
echo ""

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl:"
    echo "   brew install kubectl"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    echo "❌ helm not found. Please install helm:"
    echo "   brew install helm"
    exit 1
fi

# Check Minikube
if ! minikube status &> /dev/null; then
    echo "❌ Minikube not running. Please start Minikube:"
    echo "   minikube start --driver=docker --memory=4096 --cpus=2"
    exit 1
fi

echo "✓ Prerequisites check passed"
echo ""

# Set kubectl context to minikube
kubectl config use-context minikube

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Build Docker image for Minikube
echo "🏗️  Building Airflow Docker image..."
cd "$PROJECT_DIR"
docker build -t airflow_project-airflow-webserver:latest .

# Load image into Minikube
echo "📦 Loading image into Minikube..."
minikube image load airflow_project-airflow-webserver:latest

echo ""

# Deploy with Helm
echo "⚓ Deploying with Helm..."
helm upgrade --install airflow "$HELM_CHART_DIR" \
    --namespace $NAMESPACE \
    --create-namespace \
    --wait \
    --timeout 10m

echo ""
echo "✅ Airflow deployed successfully!"
echo ""

# Show status
echo "📊 Deployment Status:"
kubectl get pods -n $NAMESPACE
echo ""

# Port forward to access webserver
echo "🌐 Setting up port forwarding..."
echo "   Access Airflow UI at: http://localhost:8080"
echo "   Press Ctrl+C to stop port forwarding"
echo ""

kubectl port-forward -n $NAMESPACE svc/airflow-airflow-helm-webserver 8080:8080