# Scraper Platform - Complete Folder Structure & File Details

**Last Updated**: 2025-12-12
**Version**: 5.0
**Purpose**: Enterprise-grade web scraping and automation platform

---

## 📁 Root Directory Structure

```
scraper-platform/
├── 📄 Configuration Files
├── 📂 Core Directories
├── 📂 Source Code (src/)
├── 📂 Documentation (docs/)
├── 📂 Examples
├── 📂 Data Storage
└── 📂 Tools & Scripts
```

---

## 📄 Root-Level Files

### Entry Points
| File | Purpose | Functionality |
|------|---------|---------------|
| `main.py` | CLI entry point | Main command-line interface for running pipelines |
| `run_ui.py` | Desktop UI launcher | Starts the PySide6 desktop application |
| `setup.py` | Package installer | Python package setup and installation |

### Configuration
| File | Purpose | Functionality |
|------|---------|---------------|
| `pyproject.toml` | Project metadata | Modern Python project configuration |
| `setup.cfg` | Setup configuration | Additional setup parameters |
| `requirements.txt` | Dependencies | Python package dependencies |
| `.env.example` | Environment template | Example environment variables |

### Documentation (Root)
| File | Purpose | Functionality |
|------|---------|---------------|
| `README.md` | Main README | Project overview and quick start |
| `DOCS_README.md` | Documentation index | Guide to all documentation |
| `LICENSE` | License file | MIT License |

### Docker
| File | Purpose | Functionality |
|------|---------|---------------|
| `Dockerfile` | Container definition | Docker image configuration |
| `docker-compose.yml` | Multi-container setup | Orchestrates all services |

### Scripts
| File | Purpose | Functionality |
|------|---------|---------------|
| `run_alfabeta.bat` | Windows launcher | Quick launch script for AlfaBeta scraper |
| `sync-directories.py` | Directory sync | Synchronizes directory structures |
| `create_airflow_config.py` | Airflow setup | Generates Airflow configuration |

---

## 📂 Source Code Structure (`src/`)

### Core Modules

#### 🤖 **agents/** - AI Agent Framework
Self-healing, intelligent scraping agents with LLM integration.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `agent_framework.py` | Agent base framework | Agent lifecycle, state management |
| `agent_orchestrator.py` | Agent coordination | Orchestrates multiple agents |
| `scraper_brain.py` | Main scraper AI | Intelligent scraping decisions |
| `llm.py` | LLM integration | OpenAI/Claude API wrapper |
| `llm_selector_engine.py` | Selector generation | AI-powered CSS selector creation |
| `llm_debugger.py` | AI debugger | Automatic error diagnosis and fixes |
| `deepagent_repair_engine.py` | Self-healing engine | Automatic repair of broken scrapers |
| `anomaly_detector.py` | Anomaly detection | Detects scraping anomalies |
| `drift_analyzer.py` | Website change detection | Analyzes website structural changes |
| `patch_proposer.py` | Fix suggestions | Proposes patches for broken scrapers |
| `replay_validator.py` | Validation engine | Validates scraper outputs |

**Functionality**: Provides intelligent, self-healing scraping capabilities with LLM-powered selector generation, automatic error recovery, and continuous monitoring.

---

#### 🧠 **ai/** - AI & Machine Learning
Advanced AI capabilities beyond agents.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `langgraph_workflow.py` | LangGraph workflows | Complex AI workflow orchestration |
| `rag_pipeline.py` | RAG implementation | Retrieval-Augmented Generation for scraping |

**Functionality**: Implements advanced AI workflows, RAG pipelines for context-aware scraping, and LangGraph-based agent orchestration.

---

#### 🌐 **api/** - REST API Server
FastAPI-based REST API for programmatic access.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `app.py` | FastAPI application | Main API server setup |
| `models.py` | Pydantic models | API request/response schemas |
| `graphql_api.py` | GraphQL endpoint | GraphQL API implementation |
| `webhooks.py` | Webhook handlers | External webhook integrations |
| `startup_checks.py` | Health checks | API startup validation |

**Routes** (`routes/`):
- `airflow_control.py` - Airflow DAG management
- `airflow_proxy.py` - Airflow UI proxy
- `runs.py` - Pipeline run management
- `sessions.py` - Session management
- `audit.py` - Audit log access
- `health.py` - Health check endpoint
- `logs.py` - Log retrieval
- `steps.py` - Step-level details
- `costs.py` - Cost tracking
- `deploy.py` - Deployment management
- `integration.py` - Third-party integrations
- `source_health.py` - Source health monitoring
- `variants.py` - A/B testing variants

**Functionality**: Provides comprehensive REST and GraphQL APIs for pipeline management, monitoring, and integration with external systems.

---

#### 🖥️ **ui/** - Desktop User Interface
PySide6-based desktop application with modern UI.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `main_window.py` | Main window | Primary UI container and layout (2300+ lines) |
| `modern_components.py` | Modern UI widgets | 6 production-ready components (462 lines) |
| `theme.py` | Theme system | Light/dark themes, color schemes |
| `workflow_graph.py` | Visual DAG viewer | Interactive workflow visualization |
| `job_manager.py` | Job management | Multi-process job execution |
| `airflow_service.py` | Airflow integration | Airflow service management |
| `logging_handler.py` | UI logging | Custom log handler for UI |
| `path_utils.py` | File utilities | Path opening, file management |

**Components** (`modern_components.py`):
1. **IconSidebar** - 80px icon-based navigation
2. **Card** - Modern card component
3. **ActivityCard** - Activity feed cards
4. **ActivityPanel** - 350px activity panel
5. **SectionHeader** - Styled section headers
6. **BulletList** - Modern bullet lists

**Functionality**: Full-featured desktop application for pipeline management, real-time monitoring, log viewing, and workflow visualization.

---

#### 🔄 **pipeline/** - Pipeline Execution Engine
Core pipeline compilation and execution.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `compiler.py` | Pipeline compiler | Compiles YAML to executable pipelines |
| `runner.py` | Pipeline executor | Executes compiled pipelines |
| `registry.py` | Component registry | Manages all pipeline components |
| `graph.py` | DAG graph | Dependency graph management |
| `step.py` | Step definition | Individual pipeline step logic |

**Functionality**: Compiles YAML-based pipeline definitions into executable workflows, manages dependencies, and executes steps in correct order.

---

#### 🏃 **entrypoints/** - Application Entry Points
High-level execution interfaces.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `run_pipeline.py` | Pipeline runner | Main pipeline execution function |
| `cli_runner.py` | CLI interface | Command-line pipeline execution |
| `airflow_runner.py` | Airflow integration | Airflow DAG execution wrapper |

**Functionality**: Provides multiple execution modes (CLI, API, Airflow) with consistent interface.

---

#### 🕷️ **scrapers/** - Source-Specific Scrapers
Individual scraper implementations for each data source.

**Structure**:
```
scrapers/
├── alfabeta/           # AlfaBeta scraper
│   ├── scraper.py      # Main scraper logic
│   ├── selectors.py    # CSS selectors
│   └── samples/        # Sample data for testing
├── lafa/               # LAFA scraper
├── quebec/             # Quebec scraper
└── template/           # Template for new scrapers
```

**Functionality**: Source-specific scraping logic with customized selectors, parsing rules, and data extraction.

---

#### ⚙️ **processors/** - Data Processing Modules
Modular data transformation and enrichment.

| Subdirectory | Purpose | Key Components |
|--------------|---------|----------------|
| `parse/` | HTML parsing | BeautifulSoup, lxml integration |
| `llm/` | LLM processing | AI-powered data extraction |
| `enrichment/` | Data enrichment | Data augmentation and enhancement |
| `exporters/` | Data export | Export to various formats |
| `qc/` | Quality control | Domain-driven QC framework |
| `pdf/` | PDF processing | PDF text extraction |
| `pcid/` | PCID handling | Product catalog ID management |

**QC Framework** (`qc/`):
- `domain/` - Business logic
- `application/` - Use cases
- `infrastructure/` - Implementation

**Functionality**: Modular data processing pipeline with parsing, transformation, enrichment, quality control, and export capabilities.

---

#### 🚀 **engines/** - Execution Engines
Browser automation and HTTP engines.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `playwright_engine.py` | Playwright browser | Headless browser automation |
| `selenium_engine.py` | Selenium browser | Alternative browser engine |
| `http_engine.py` | HTTP client | Fast HTTP-only scraping |
| `stealth_engine.py` | Anti-detection | Stealth browsing techniques |

**Functionality**: Multiple execution engines for different scraping needs - browser automation for JavaScript-heavy sites, HTTP for fast static scraping.

---

#### 📊 **run_tracking/** - Execution Tracking
Pipeline run recording and analysis.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `recorder.py` | Run recorder | Records pipeline execution details |
| `models.py` | Data models | Run, step, and metadata models |
| `query.py` | Query interface | Retrieve historical run data |
| `stats.py` | Statistics | Run statistics and aggregations |

**Functionality**: Comprehensive tracking of pipeline runs, steps, errors, metrics, and statistics with SQLite storage.

---

#### 📅 **scheduler/** - Job Scheduling
Airflow integration and smart scheduling.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `scheduler_db_adapter.py` | Database adapter | Airflow metadata access |
| `smart_scheduler.py` | Intelligent scheduling | AI-powered schedule optimization |
| `run_optimizer.py` | Run optimization | Resource allocation optimization |

**Functionality**: Integrates with Apache Airflow for robust scheduling, with intelligent optimization based on historical performance.

---

#### 🔐 **security/** - Security & Encryption
Data protection and secure credential management.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `crypto_utils.py` | Encryption | AES encryption for secrets |
| `credential_manager.py` | Credential storage | Secure API key management |
| `proxy_manager.py` | Proxy rotation | Manages proxy pools |

**Functionality**: Encrypts sensitive data (API keys, passwords), manages proxies, and ensures secure credential handling.

---

#### 📝 **common/** - Common Utilities
Shared utilities across the platform.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `logging_utils.py` | Structured logging | JSON structured logging |
| `config_loader.py` | Configuration | YAML config loading |
| `retry.py` | Retry logic | Exponential backoff retry |
| `cache.py` | Caching | In-memory and disk caching |
| `http_utils.py` | HTTP helpers | Request utilities |

**Functionality**: Centralized utilities for logging, configuration, retries, caching, and HTTP operations.

---

#### 🔄 **versioning/** - Version Control
Data versioning and snapshot management.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `version_manager.py` | Version tracking | Tracks data versions |
| `snapshot.py` | Snapshots | Creates point-in-time snapshots |
| `diff.py` | Diff engine | Compares versions |

**Functionality**: Version control for scraped data, configuration, and selectors with diff and rollback capabilities.

---

#### 📋 **audit/** - Audit Logging
Comprehensive audit trail.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `audit_logger.py` | Audit logging | Records all system actions |
| `models.py` | Audit models | Audit event schemas |

**Functionality**: Immutable audit log of all system actions for compliance and debugging.

---

#### 🎯 **orchestration/** - Workflow Orchestration
Complex workflow management.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `orchestrator.py` | Workflow engine | Orchestrates complex workflows |
| `task_router.py` | Task routing | Routes tasks to workers |

**Functionality**: Manages complex multi-step workflows with dependencies and conditional logic.

---

#### 📦 **sessions/** - Session Management
User session tracking.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `session_manager.py` | Session handling | Creates and manages sessions |
| `models.py` | Session models | Session data structures |

**Functionality**: Tracks user sessions, browser sessions, and execution context.

---

#### 🧪 **tests_replay/** - Testing & Replay
Record and replay testing.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `replay_engine.py` | Replay engine | Replays recorded sessions |
| `recorder.py` | Session recorder | Records scraping sessions |

**Functionality**: Records scraping sessions for testing and validation, enables replay for debugging.

---

#### 📊 **observability/** - Monitoring & Observability
System monitoring and telemetry.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `metrics.py` | Metrics collection | Prometheus metrics |
| `tracing.py` | Distributed tracing | OpenTelemetry integration |
| `alerts.py` | Alerting | Alert management |

**Functionality**: Comprehensive monitoring with metrics, tracing, and alerting for production environments.

---

#### 🛠️ **devtools/** - Developer Tools
Development and debugging utilities.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `debugger.py` | Debugging tools | Interactive debugger |
| `profiler.py` | Performance profiling | Code profiling |

**Functionality**: Developer tools for debugging, profiling, and development workflow.

---

#### 🏛️ **governance/** - Data Governance
Data quality and compliance.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `data_quality.py` | Quality checks | Data validation rules |
| `compliance.py` | Compliance | GDPR, privacy compliance |

**Functionality**: Ensures data quality and regulatory compliance.

---

#### 🔌 **integrations/** - Third-Party Integrations
External service integrations.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `slack.py` | Slack integration | Slack notifications |
| `email.py` | Email notifications | SMTP email sending |
| `webhook.py` | Webhook sender | HTTP webhook calls |

**Functionality**: Integrates with external services for notifications and data export.

---

#### 📊 **etl/** - ETL Pipelines
Extract, Transform, Load operations.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `etl_engine.py` | ETL orchestration | Manages ETL workflows |
| `transformers.py` | Data transformation | Data mapping and transforms |

**Functionality**: ETL pipeline framework for data warehouse integration.

---

#### 🤝 **client_api/** - Client Libraries
SDK for programmatic access.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `client.py` | Python client | SDK for API access |

**Functionality**: Python SDK for easy API integration.

---

#### 🧰 **utils/** - General Utilities
Miscellaneous helper functions.

| File | Purpose | Key Functions |
|------|---------|---------------|
| `file_utils.py` | File operations | File I/O helpers |
| `date_utils.py` | Date handling | Date parsing and formatting |
| `string_utils.py` | String operations | String manipulation |

**Functionality**: General-purpose utility functions.

---

## 📂 Configuration Directory (`config/`)

```
config/
├── sources/              # Source-specific configs
│   ├── alfabeta.yaml
│   ├── lafa.yaml
│   └── ...
├── env/                  # Environment configs
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
└── secrets/              # Encrypted secrets
    └── encrypted_secrets.json
```

**Functionality**: Centralized configuration management with environment-specific overrides and secure secret storage.

---

## 📂 DSL Directory (`dsl/`)

```
dsl/
├── components.yaml       # Reusable pipeline components
└── llm_compiler.py       # LLM-powered pipeline generation
```

**Functionality**: Domain-Specific Language for pipeline definition with AI-powered pipeline generation.

---

## 📂 DAGs Directory (`dags/`)

Airflow DAG definitions for scheduled execution.

| File | Purpose |
|------|---------|
| `scraper_alfabeta.py` | AlfaBeta DAG |
| `scraper_lafa.py` | LAFA DAG |
| `scraper_quebec.py` | Quebec DAG |
| `agent_orchestrator.py` | Agent orchestration DAG |
| `etl_postrun_example.py` | ETL post-processing |
| `replay_runner.py` | Replay testing DAG |

**Functionality**: Apache Airflow DAGs for production scheduling and orchestration.

---

## 📂 Sources Directory (`sources/`)

Source-specific pipeline implementations.

```
sources/
├── argentina/
│   ├── pipeline.py       # Argentina pipeline
│   ├── parse_rules.py    # Parsing rules
│   └── map_rules.py      # Data mapping
├── chile/
├── lafa/
└── quebec/
```

**Functionality**: Source-specific pipeline logic, parsing rules, and data mappings.

---

## 📂 Examples Directory (`examples/`)

### Modern UI Reference (`modern-ui-reference/`)
Standalone demo application showcasing the Modern UI components.

```
modern-ui-reference/
├── main.py               # Demo application (198 lines)
├── theme.qss             # Stylesheet (200 lines)
├── components/           # Reference components
│   ├── sidebar.py        # 80px icon sidebar
│   ├── main_content.py   # Main content panel
│   └── email_panel.py    # Activity panel
└── docs/
    ├── README.md
    ├── FEATURES.md
    └── ARCHITECTURE.md
```

**Functionality**: Complete working example of Modern UI implementation for reference and testing.

---

## 📂 Documentation Directory (`docs/`)

### Modern UI Documentation (`modern-ui/`)

```
docs/modern-ui/
├── README.md                    # Master overview
├── INDEX.md                     # Complete index
├── MODERN_UI_README.md          # Quick start
├── MODERN_UI_QUICKSTART.md      # 5-minute guide
├── MODERN_UI_INDEX.md           # Navigation hub
├── MODERN_UI_SUMMARY.md         # Technical summary
├── INTEGRATION_GUIDE.md         # Integration guide
├── DELIVERABLES.md              # Deliverables list
├── VALIDATION_REPORT.md         # Quality report
├── END_TO_END_SUMMARY.md        # Sanitization summary
├── FINAL_SUMMARY.md             # Implementation summary
├── FOLDER_STRUCTURE.md          # Organization guide
└── validate_modern_ui.py        # Validation script
```

**Total**: 13 files (12 docs + 1 script)
**Lines**: ~5,000 lines of documentation

**Functionality**: Comprehensive documentation for Modern UI implementation with guides, examples, and validation tools.

---

## 📂 Data Storage Directories

### Input (`input/`)
Raw input files and data sources.

### Output (`output/`)
```
output/
├── data/                 # Scraped data
├── logs/                 # Execution logs
└── version_snapshots/    # Version snapshots
```

### Logs (`logs/`)
```
logs/
├── run_tracking.sqlite   # Run history database
├── ui_logs.json          # UI logs (persistent)
└── event_history.json    # Event log
```

### Database (`db/`)
SQLite databases for tracking and metadata.

### Sessions (`sessions/`)
Browser session recordings.

### Replay Snapshots (`replay_snapshots/`)
Recorded sessions for replay testing.

---

## 📂 Tools & Dependencies

### Tools (`tools/`)
Development and maintenance scripts.

### Scraper Dependencies (`scraper-deps/`)
Shared dependencies for scrapers.

### Schemas (`schemas/`)
JSON schemas for data validation.

---

## 🔑 Key Files Summary

### Most Important Files (Top 20)

| File | Lines | Purpose |
|------|-------|---------|
| `src/ui/main_window.py` | 2300+ | Desktop UI main window |
| `src/agents/scraper_brain.py` | 1500+ | AI scraper intelligence |
| `src/pipeline/compiler.py` | 800+ | Pipeline compilation |
| `src/pipeline/runner.py` | 600+ | Pipeline execution |
| `src/ui/modern_components.py` | 462 | Modern UI components |
| `src/processors/qc/*.py` | 400+ | Quality control framework |
| `src/engines/playwright_engine.py` | 500+ | Browser automation |
| `src/api/app.py` | 400+ | REST API server |
| `src/agents/deepagent_repair_engine.py` | 600+ | Self-healing engine |
| `src/run_tracking/recorder.py` | 300+ | Run tracking |

---

## 📊 Project Statistics

- **Total Python Files**: 200+
- **Total Lines of Code**: 50,000+
- **Total Documentation**: 5,000+ lines
- **Modules**: 35+
- **Components**: 100+
- **API Endpoints**: 30+
- **DAGs**: 15+

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   CLI    │  │ Desktop  │  │ REST API │              │
│  │  main.py │  │  UI      │  │          │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
└───────┼─────────────┼─────────────┼─────────────────────┘
        │             │             │
┌───────▼─────────────▼─────────────▼─────────────────────┐
│              Orchestration Layer                         │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────┐     │
│  │   Pipeline   │  │  Scheduler  │  │  Agents    │     │
│  │   Engine     │  │  (Airflow)  │  │  AI Brain  │     │
│  └──────┬───────┘  └──────┬──────┘  └─────┬──────┘     │
└─────────┼──────────────────┼────────────────┼───────────┘
          │                  │                │
┌─────────▼──────────────────▼────────────────▼───────────┐
│               Execution Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Scrapers │  │ Engines  │  │Process   │              │
│  │ (Source) │  │(Browser) │  │(ETL/QC)  │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
└───────┼─────────────┼──────────────┼─────────────────────┘
        │             │              │
┌───────▼─────────────▼──────────────▼─────────────────────┐
│                Storage & Tracking                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ SQLite   │  │  Files   │  │ Versions │              │
│  │ Tracking │  │  Output  │  │Snapshots │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

**Last Updated**: 2025-12-12
**Maintained By**: Scraper Platform Team
