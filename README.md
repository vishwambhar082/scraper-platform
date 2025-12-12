# Scraper Platform v5.0 🚀

> **AI-powered web scraping platform with autonomous agent system**

## Overview

The Scraper Platform is a unified pipeline architecture for scalable, maintainable web scraping. It features self-healing scrapers using LLMs for anomaly detection and patch generation, orchestrated by Apache Airflow DAGs.

## Key Features

- **🤖 Autonomous Agents**: Self-healing scrapers with LLM-powered repair capabilities
- **🔗 Unified Pipeline**: Single execution model replacing multiple orchestrators
- **⚡ Parallel Execution**: Automatic parallelization of independent steps
- **📋 Type-Safe Steps**: Clear step types (FETCH, PARSE, TRANSFORM, VALIDATE, ENRICH, EXPORT)
- **🛡️ Robust Error Handling**: Built-in retry logic with exponential backoff
- **📊 Comprehensive Tracking**: Full monitoring and logging of all pipeline steps

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
cp config/env/example.env .env
# Edit .env with your settings

# Create necessary directories (or run scripts/setup_dev.sh)
mkdir -p sessions/cookies sessions/logs output/alfabeta/daily input
```

## Running the Platform

### Option 1: Using Docker (Recommended)

```bash
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
│   ├── api/               # API endpoints
│   ├── engines/           # Scraping engines
│   ├── pipeline/          # Pipeline system
│   ├── scrapers/          # Source-specific scrapers
│   └── ...
├── tests/                 # Test suite
└── tools/                 # Utility tools
```

## Available Sources

- Alfabeta
- Argentina
- Chile
- LAFA
- Quebec

## Documentation

- [Architecture Overview](docs/architecture/ARCHITECTURE_V5.md)
- [Quick Start Guide](docs/tutorials/QUICK_START_V5.md)
- [Running Without Airflow](docs/guides/RUN_WITHOUT_AIRFLOW.md)
- [Docker Instructions](docs/guides/DOCKER_INSTRUCTIONS.md)
- [Troubleshooting](docs/troubleshooting/)
- [Developer Setup](docs/DEV_SETUP.md)

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
**Version**: 5.0.0  
**Status**: ✅ Production Ready