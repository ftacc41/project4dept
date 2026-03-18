# Phase 1 Installation & Startup Guide

## Prerequisites

Before starting, ensure you have:

1. **Docker Desktop** installed
   - macOS: https://www.docker.com/products/docker-desktop
   - Windows: https://www.docker.com/products/docker-desktop (with WSL2)
   - Linux: Install `docker` + `docker-compose`

2. **~4GB RAM** available for Docker
   - Configure in Docker Desktop → Preferences → Resources

3. **~2GB disk space**

## Quick Start (5 Minutes)

### 1. Start Docker Desktop
- macOS: Click Docker icon in Applications
- Windows: Click Docker Desktop shortcut
- Linux: `systemctl start docker` (or equivalent)

Wait for Docker daemon to start (right-click icon should show "Docker is running")

### 2. Navigate to project
```bash
cd /Users/macbook/Desktop/CODING_PROJECTS/airflow_project
```

### 3. Start Airflow
```bash
# Option A: Using script
bash start.sh

# Option B: Using docker-compose directly
docker-compose up -d
```

This will:
- Initialize PostgreSQL database
- Build custom Airflow image
- Start scheduler, webserver, and dependenciesWait ~30 seconds for initialization

### 4. Access Airflow UI
Open http://localhost:8080 in browser
- Username: `admin`
- Password: `admin`

### 5. Trigger First DAG
- Find `marketing_data_extract_load` in DAG list
- Click the DAG name
- Click "Trigger DAG" button (top-right)
- Watch tasks execute in real-time

## Monitoring

### View Logs (Real-Time)
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f airflow-scheduler
docker-compose logs -f airflow-webserver
docker-compose logs -f postgres
```

### Check Service Status
```bash
docker-compose ps
```

Expected output:
```
NAME                  COMMAND              STATUS
airflow-webserver     webserver            Up (healthy)
airflow-scheduler     scheduler            Up
postgres              postgres             Up (healthy)
redis                 redis-server         Up (healthy)
```

### Execute Commands in Container
```bash
# Bash into webserver
docker-compose exec airflow-webserver bash

# Run Python in container
docker-compose exec airflow-webserver python -c "import pandas; print(pandas.__version__)"

# View Airflow logs
docker-compose exec airflow-webserver ls /home/airflow/airflow/logs/
```

## Cleanup

### Stop Services (Keep Data)
```bash
docker-compose stop
```

### Stop & Remove (Keep Volumes)
```bash
docker-compose down
```

### Full Reset (Delete Everything)
```bash
docker-compose down -v
```

⚠️ This deletes:
- All containers
- Database data
- DAG execution history

## Troubleshooting

### Port 8080 Already in Use
```bash
# Find what's using port 8080
lsof -i :8080

# Kill the process
kill -9 <PID>
```

### Docker Daemon Not Running
```bash
# Check if daemon is running
docker ps

# If error: "Cannot connect to Docker daemon"
# → Start Docker Desktop manually
```

### PostgreSQL Connection Refused
```bash
# Wait 30 seconds, then restart scheduler
docker-compose restart airflow-scheduler

# Check logs
docker-compose logs postgres
```

### DAG Not Appearing After 5 Minutes
```bash
# Force DAG refresh
docker-compose exec airflow-scheduler airflow dags reparse

# Or restart scheduler
docker-compose restart airflow-scheduler
```

### Insufficient Disk Space
```bash
# Check Docker storage
docker system df

# Remove unused images/containers
docker system prune -a
```

## Next Steps

Once Airflow is running:

1. **Trigger the DAG** to test pipeline
2. **Monitor execution** in Airflow UI
3. **View generated data** in `/tmp/airflow_data/`
4. **Read Phase 1 Guide** → `docs/PHASE_1_SETUP.md`
5. **Proceed to Phase 2** when ready

---

**Having issues?** Check [Phase 1 Troubleshooting](PHASE_1_SETUP.md#-troubleshooting)
