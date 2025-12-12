#!/usr/bin/env bash
set -euo pipefail

AIRFLOW_HOME=${AIRFLOW_HOME:-/app/airflow}
mkdir -p "${AIRFLOW_HOME}/logs" "${AIRFLOW_HOME}/dags" "${AIRFLOW_HOME}/plugins"

export AIRFLOW_HOME

if [ -z "${AIRFLOW__CORE__FERNET_KEY:-}" ]; then
  echo "[docker-init] AIRFLOW__CORE__FERNET_KEY is not set. Please set it in your environment."
  exit 1
fi

echo "[docker-init] Initializing Airflow database..."
airflow db init

ADMIN_USER=${AIRFLOW_ADMIN_USER:-admin}
ADMIN_PWD=${AIRFLOW_ADMIN_PASSWORD:-admin}
ADMIN_EMAIL=${AIRFLOW_ADMIN_EMAIL:-admin@example.com}

if ! airflow users list | grep -q "${ADMIN_USER}"; then
  echo "[docker-init] Creating admin user ${ADMIN_USER}"
  airflow users create \
    --username "${ADMIN_USER}" \
    --password "${ADMIN_PWD}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email "${ADMIN_EMAIL}"
else
  echo "[docker-init] Admin user ${ADMIN_USER} already exists"
fi

echo "[docker-init] Airflow init complete."

