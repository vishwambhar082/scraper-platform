# System Overview

This platform orchestrates source-aware scraping pipelines, supporting both legacy and pipeline-pack agent frameworks. Core components include Airflow DAGs for scheduling, configurable engines (HTTP-first with experimental browser backends), and exporters for database or file delivery.

## Components
- **Schedulers**: Airflow DAGs such as `agent_orchestrator_pack.py` trigger configured pipelines.
- **Agents**: Legacy agents under `src/agents/` and experimental agents under `src/pipeline_pack/agents/` handle fetch, parse, normalize, and export tasks.
- **Engines**: HTTP engine is production-ready; browser engines exist as stubs until implemented or disabled.
- **Exporters**: Database and file exporters surface results for downstream consumers.

## Configurations
- Agent defaults and pipelines live under `config/agents/` and `config/pipeline_pack/`.
- Deployment environments rely on optional dependencies (e.g., `psycopg2`, `selenium`) only when the related features are enabled.
- Frontend dashboard (`frontend-dashboard/`) surfaces run health, logs, and export statuses.

## Current posture
Use the HTTP engine by default. Clearly mark any pipeline-pack usage as experimental until browser engines are completed and dependency gating is enforced.
