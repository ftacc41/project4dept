#!/bin/bash
# Quick start script for Phase 1

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Marketing Analytics Platform - Local Startup"
echo "================================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop:"
    echo "   https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check Docker daemon
if ! docker ps &> /dev/null; then
    echo "❌ Docker daemon not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✓ Docker is running"
echo ""

# Create .env if doesn't exist
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "✓ Created .env from .env.example"
fi

# Check Docker Compose version
echo "Checking docker-compose..."
docker-compose --version
echo ""

# Start services
echo "📦 Starting Airflow services..."
docker-compose -f "$PROJECT_DIR/docker-compose.yml" up -d

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check status
echo ""
echo "📊 Service Status:"
docker-compose -f "$PROJECT_DIR/docker-compose.yml" ps

echo ""
echo "✅ Airflow is starting up!"
echo ""
echo "🌐 Access Airflow UI at: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "📝 View logs:"
echo "   docker-compose -f $PROJECT_DIR/docker-compose.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker-compose -f $PROJECT_DIR/docker-compose.yml down"
