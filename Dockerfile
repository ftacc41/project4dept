# Multi-stage Airflow image for production use
# Stage 1: Builder
FROM apache/airflow:2.8.1-python3.11 AS builder

USER root

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --user --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Runtime
FROM apache/airflow:2.8.1-python3.11

USER root

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy Python packages from builder
COPY --from=builder /home/airflow/.local /home/airflow/.local

# Install dbt-bigquery in an isolated venv to avoid Airflow dependency conflicts
# PIP_USER=false overrides the base image's global --user flag, which is invalid inside a venv
RUN python -m venv /home/airflow/dbt-venv \
    && PIP_USER=false /home/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-bigquery

# Set environment variables
ENV PATH=/home/airflow/.local/bin:$PATH
ENV PYTHONPATH=/home/airflow/plugins:$PYTHONPATH
ENV AIRFLOW_HOME=/home/airflow/airflow
ENV DBT_BIN=/home/airflow/dbt-venv/bin/dbt

# Copy project files
COPY --chown=airflow:airflow dags/ /home/airflow/airflow/dags/
COPY --chown=airflow:airflow plugins/ /home/airflow/airflow/plugins/
COPY --chown=airflow:airflow scripts/ /home/airflow/scripts/
COPY --chown=airflow:airflow dbt/ /home/airflow/dbt/
COPY --chown=airflow:airflow .env* /home/airflow/airflow/

# dbt profiles — GCP key is mounted at runtime via K8s secret
RUN mkdir -p /home/airflow/.dbt /home/airflow/.gcp
COPY --chown=airflow:airflow dbt/profiles.yml /home/airflow/.dbt/profiles.yml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080')"

WORKDIR /home/airflow

USER airflow
