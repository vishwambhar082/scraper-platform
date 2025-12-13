# Scraper Platform v5.0

> **Enterprise-grade web scraping platform with autonomous agent system**

## Overview

The Scraper Platform is a unified pipeline architecture for scalable, maintainable web scraping. It features self-healing scrapers using LLMs for anomaly detection and patch generation, orchestrated by Apache Airflow DAGs.

**Recent Refactor (2025-12-13)**: Platform has undergone comprehensive security hardening and code consolidation. See [REFACTOR_LOG.md](REFACTOR_LOG.md) for details.

## Key Features

- **Autonomous Agents**: Self-healing scrapers with LLM-powered repair capabilities
- **Unified Pipeline**: Single execution model replacing multiple orchestrators
- **Parallel Execution**: Automatic parallelization of independent steps
- **Type-Safe Steps**: Clear step types (FETCH, PARSE, TRANSFORM, VALIDATE, ENRICH, EXPORT)
- **Robust Error Handling**: Built-in retry logic with exponential backoff
- **Comprehensive Tracking**: Full monitoring and logging of all pipeline steps
- **Structured Logging**: Enterprise-grade JSON logging with context management and sensitive data masking
- **Production-Ready**: Enhanced security, health checks, and configuration management

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (recommended for Airflow)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd scraper-platform

# Install dependencies
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# IMPORTANT: Edit .env with required settings (see below)

# Create necessary directories (or run scripts/setup_dev.sh)
mkdir -p sessions/cookies sessions/logs output/alfabeta/daily input
```

### Required Environment Variables

Before running the platform, configure these **required** variables in `.env`:

```bash
# Database (REQUIRED for Docker/Airflow)
POSTGRES_PASSWORD=your_secure_password_here
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:your_password@postgres/airflow
AIRFLOW__CORE__FERNET_KEY=your_fernet_key_here

# API Security (REQUIRED for production)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000  # Comma-separated list

# Database Connection (REQUIRED if not using defaults)
DB_URL=postgresql://user:password@localhost:5432/scraper_platform
```

Generate Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

See [.env.example](.env.example) for complete configuration options.

## Running the Platform

### Option 1: Using Docker (Recommended)

```bash
# IMPORTANT: Set required env vars in .env first (see above)

# Build and start services
docker-compose up -d

# Access Airflow UI at http://localhost:8080
# Default credentials: admin/admin
```

### Option 2: Direct Execution (No Airflow)

```bash
# Run a scraper directly (canonical entrypoint)
python -m src.entrypoints.run_pipeline --source alfabeta --environment dev

# Run with the desktop UI
python run_ui.py
```

## Health Check Endpoints

The platform provides production-ready health check endpoints for monitoring:

- **`GET /health/live`** - Liveness probe (process running)
- **`GET /health/ready`** - Readiness probe (dependencies healthy, returns 503 if not ready)
- **`GET /health/db`** - Database connectivity check
- **`GET /health/secrets`** - Environment variable validation

Use these for Kubernetes readiness/liveness probes or monitoring systems.

## Project Structure

```
scraper-platform/
├── config/                 # Configuration files
│   ├── env/               # Environment configs
│   ├── sources/           # Source-specific configs
│   └── ...
├── dags/                  # Airflow DAG definitions
├── db/                    # Database migrations
├── docs/                  # Documentation
│   ├── architecture/      # Architecture docs
│   ├── guides/            # User guides
│   ├── reference/         # Reference materials
│   ├── tutorials/         # Tutorials
│   └── troubleshooting/   # Troubleshooting guides
├── dsl/                   # Pipeline definitions
├── schemas/               # Data schemas
├── src/                   # Source code
│   ├── agents/            # Autonomous agents
│   ├── api/               # API endpoints and health checks
│   ├── common/            # Shared types and utilities
│   ├── engines/           # Scraping engines
│   ├── pipeline/          # Unified pipeline system
│   ├── processors/        # Data processors and exporters
│   ├── scrapers/          # Source-specific scrapers
│   ├── ui/                # Desktop UI application
│   └── ...
├── tests/                 # Test suite
├── tools/                 # Utility tools
├── .env.example           # Environment variable template
└── REFACTOR_LOG.md        # Recent refactor documentation
```

**Note**: `src/core_kernel/`, `src/orchestration/`, and `src/pipeline_pack/` have been removed in v5.0 refactor.

## Available Sources

- Alfabeta
- Argentina
- Chile
- LAFA
- Quebec

## Documentation

- [Refactor Log](REFACTOR_LOG.md) - **Recent changes, security fixes, breaking changes**
- [Architecture Overview](docs/architecture/ARCHITECTURE_V5.md)
- [Quick Start Guide](docs/tutorials/QUICK_START_V5.md)
- [Running Without Airflow](docs/guides/RUN_WITHOUT_AIRFLOW.md)
- [Docker Instructions](docs/guides/DOCKER_INSTRUCTIONS.md)
- [Troubleshooting](docs/troubleshooting/)
- [Developer Setup](docs/DEV_SETUP.md)

### Structured Logging Documentation

- [Quick Start](src/app_logging/QUICK_START.md) - Get started with structured logging in 5 minutes
- [Complete Guide](src/app_logging/STRUCTURED_LOGGING_GUIDE.md) - Comprehensive structured logging documentation
- [Module README](src/app_logging/README.md) - App logging module overview
- [Examples](src/app_logging/examples.py) - Runnable code examples

## Security & Configuration

### Security Improvements (v5.0 Refactor)

✅ **Fixed Critical Vulnerabilities**:
- CORS misconfiguration (wildcard with credentials)
- Command injection in setup scripts
- SQL injection in database exporters
- Hardcoded PostgreSQL credentials
- Insecure proxy credential exposure

See [REFACTOR_LOG.md](REFACTOR_LOG.md) for complete security audit results.

### Configuration Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Set strong passwords** for `POSTGRES_PASSWORD` and database connections
3. **Whitelist CORS origins** - Never use `*` in production
4. **Use HTTPS** for Vault and external services
5. **Rotate Fernet keys** periodically in production

### Deprecated Configuration

The following environment variables are **deprecated** (use `DB_URL` instead):
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`

Migration: Convert to `DB_URL=postgresql://user:password@host:port/database`

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pipeline.py
```

### Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Formatting
black src/
```

## Diagnostics & Troubleshooting

Export comprehensive diagnostics for troubleshooting and support:

```bash
# Export diagnostics via CLI
python -m src.devtools.diagnostics_exporter --output diagnostics.zip

# Export diagnostics via UI
# File → Export Diagnostics... or Settings page → Export Diagnostics button

# Export for specific run
python -m src.devtools.diagnostics_exporter --run-id RUN-20251213-ABC123 --format html
```

The diagnostics export includes:
- System information (OS, Python, CPU, memory, disk)
- Platform configuration and version
- Database schema and table info
- Recent run history with statistics
- Recent logs (last 1000 lines, sanitized)
- Environment variables (secrets automatically redacted)
- Installed packages
- Performance metrics
- Recent errors

See [docs/DIAGNOSTICS_EXPORT.md](docs/DIAGNOSTICS_EXPORT.md) for complete documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Deployment Status

**Version**: 5.0.0
**Status**: ✅ Production Ready (Internal Enterprise)

**Recent Refactor (2025-12-13)**:
- 5 critical/high security vulnerabilities fixed
- ~2,000 lines of dead code removed
- Configuration consolidated and documented
- Health check endpoints added
- See [REFACTOR_LOG.md](REFACTOR_LOG.md) for complete details

**Ready for**:
- ✅ Internal enterprise deployment
- ✅ Docker/Kubernetes orchestration
- ✅ Multi-tenant operation

**Needs work for external SaaS**:
- ⚠️ UI module split (3,196-line file)
- ⚠️ Prometheus metrics integration
- ⚠️ Comprehensive integration tests
- ✅ Structured logging (JSON format) - **IMPLEMENTED**