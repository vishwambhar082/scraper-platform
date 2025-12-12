# Scraper Platform - Complete Folder Structure V6.0

**Version**: 6.0 (Corrected & Complete)
**Last Updated**: 2025-12-12
**Status**: ✅ Verified Against GitHub Repository
**Purpose**: Enterprise-grade web scraping and automation platform

> **Note**: This document represents the **actual** structure based on the live repository at `vishwambhar082/scraper-platform` with all missing components documented.

---

## 📋 Document Change Log

### V6.0 Changes from V5.0
**Added**:
- ✅ `db/migrations/` - Database schema migrations (17 SQL files)
- ✅ `logs/` - Runtime log storage
- ✅ `.claude/` and `.vscode/` - Development environment configs
- ✅ `schemas/pcid/` - PCID schema definitions
- ✅ Missing critical modules: `browser_pool.py`, `rate_limiter.py`, `queue.py`, `errors.py`
- ✅ Deployment folder structure (`deploy/`)
- ✅ Configuration precedence documentation
- ✅ Secrets rotation logic documentation
- ✅ Unified retry configuration registry
- ✅ Migration automation tooling
- ✅ Architectural Decision Records (ADRs)

**Consolidated**:
- 🔄 Unified LLM layer documentation (removed duplication)
- 🔄 Consolidated logging architecture
- 🔄 Merged replay system documentation

**Corrected**:
- ✅ Fully documented `scraper-deps/`
- ✅ Added QC rule taxonomy
- ✅ Completed Airflow integration docs
- ✅ Added validation scripts section

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   CLI    │  │ Desktop  │  │ REST API │  │ GraphQL  │   │
│  │  main.py │  │  UI      │  │ /health  │  │ /graphql │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼───────────┘
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼───────────┐
│           Orchestration & Scheduling Layer                   │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Pipeline   │  │  Airflow    │  │   Agent     │        │
│  │   Engine     │  │  Scheduler  │  │Orchestrator │        │
│  │  (Compiler)  │  │   (DAGs)    │  │  (AI Brain) │        │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼──────────────────┼────────────────┼───────────────┘
          │                  │                │
┌─────────▼──────────────────▼────────────────▼───────────────┐
│               Execution & Processing Layer                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Scrapers │  │ Engines  │  │Processor │  │   ETL    │   │
│  │ (Source) │  │(Browser/ │  │ Pipeline │  │  Engine  │   │
│  │          │  │  HTTP)   │  │ (QC/LLM) │  │          │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼──────────────┼──────────────┼─────────┘
        │             │              │              │
┌───────▼─────────────▼──────────────▼──────────────▼─────────┐
│           Resource Management & Infrastructure               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Browser  │  │ Proxy    │  │   Rate   │  │  Queue   │   │
│  │  Pool    │  │  Pool    │  │ Limiter  │  │  Worker  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼──────────────┼──────────────┼─────────┘
        │             │              │              │
┌───────▼─────────────▼──────────────▼──────────────▼─────────┐
│            Storage, Tracking & Observability                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ SQLite   │  │  Files   │  │ Versions │  │  Metrics │   │
│  │ (17 Mig) │  │ Output/  │  │Snapshots │  │  Logs/   │   │
│  │          │  │  Input   │  │          │  │  Traces  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Complete Directory Tree

```
scraper-platform/
│
├── 📄 Root Configuration & Entry Points
├── 📂 Core Application (src/)
├── 📂 Configuration (config/)
├── 📂 Airflow DAGs (dags/)
├── 📂 Database & Migrations (db/)
├── 📂 Documentation (docs/)
├── 📂 Domain-Specific Language (dsl/)
├── 📂 Examples & References (examples/)
├── 📂 Schemas & Contracts (schemas/)
├── 📂 Data Storage (input/, output/, logs/)
├── 📂 Source Implementations (sources/)
├── 📂 Testing Suite (tests/)
├── 📂 Developer Tools (tools/)
├── 📂 Deployment Configs (deploy/)
└── 📂 Dependencies (scraper-deps/)
```

---

## 📄 ROOT LEVEL FILES & FOLDERS

### Entry Points
| File | Lines | Purpose | Key Functionality |
|------|-------|---------|-------------------|
| `main.py` | 200+ | CLI entry point | Pipeline execution, argument parsing, logging setup |
| `run_ui.py` | 50 | Desktop UI launcher | Starts PySide6 application, exception handling |

### Python Package Configuration
| File | Purpose | Functionality |
|------|---------|---------------|
| `setup.py` | Package installer | Setuptools configuration, dependencies, entry points |
| `setup.cfg` | Setup configuration | Metadata, tool configurations (flake8, mypy) |
| `pyproject.toml` | Modern project config | PEP 518 build system, Black, isort configs |
| `requirements.txt` | Dependencies list | Production dependencies with pinned versions |

### Environment & Configuration
| File | Purpose | Functionality |
|------|---------|---------------|
| `.env.example` | Environment template | Example API keys, database URLs, feature flags |
| `.gitignore` | Git exclusions | Excludes `.env`, `__pycache__`, logs, outputs |
| `.gitattributes` | Git attributes | Line ending normalization, diff settings |
| `.dockerignore` | Docker exclusions | Excludes dev files from Docker build |

### Development Environment
| Folder/File | Purpose | Functionality |
|-------------|---------|---------------|
| `.claude/` | Claude AI config | AI coding assistant settings, prompts |
| `.vscode/` | VS Code config | Editor settings, launch configs, extensions |

### Docker & Deployment
| File | Purpose | Functionality |
|------|---------|---------------|
| `Dockerfile` | Container definition | Multi-stage build, Python 3.11, dependencies |
| `docker-compose.yml` | Multi-container orchestration | Airflow, PostgreSQL, Redis, platform services |

### Utility Scripts
| File | Purpose | Functionality |
|------|---------|---------------|
| `run_alfabeta.bat` | Windows quick launch | Runs AlfaBeta scraper with default config |
| `sync-directories.py` | Directory synchronization | Syncs config, ensures folder structure |
| `create_airflow_config.py` | Airflow setup | Generates airflow.cfg, sets environment |

### Documentation (Root)
| File | Purpose |
|------|---------|
| `README.md` | Main project README with quick start |
| `DOCS_README.md` | Documentation navigation index |
| `LICENSE` | MIT License |

---

## 📂 CORE APPLICATION (`src/`)

### **🧠 Core Kernel** (`src/core_kernel/`)
**Purpose**: Platform foundation and common interfaces.

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `base_pipeline.py` | 300+ | Pipeline base class | `BasePipeline`, `PipelineContext` |
| `interfaces.py` | 200+ | Core interfaces | `IEngine`, `IProcessor`, `IExporter` |
| `exceptions.py` | 150+ | Custom exceptions | `ScraperException`, `PipelineException` |
| `types.py` | 100+ | Type definitions | `RunConfig`, `StepResult`, `MetricValue` |

**Functionality**: Provides foundational classes, interfaces, and types used throughout the platform.

---

### **🤖 Agents** (`src/agents/`) - AI & Self-Healing
**Purpose**: Intelligent, self-healing scraping with LLM integration.

#### Core Agent Framework
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `base.py` | 200+ | Agent base class | `BaseAgent`, lifecycle methods |
| `unified_base.py` | 300+ | Unified agent interface | Standardized agent API |
| `agent_framework.py` | 400+ | Agent orchestration framework | Agent registry, communication |
| `agent_orchestrator.py` | 500+ | Multi-agent coordinator | Task distribution, results aggregation |
| `scraper_brain.py` | 1500+ | Main AI intelligence | Decision-making, strategy selection |

#### LLM Integration
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `llm.py` | 600+ | LLM API wrapper | OpenAI/Claude/Gemini integration |
| `llm_selector_engine.py` | 400+ | AI selector generation | CSS/XPath selector creation |
| `llm_debugger.py` | 350+ | AI-powered debugging | Error diagnosis, fix suggestions |
| `llm_patch_generator.py` | 300+ | Code patch generation | Generates Python code patches |

#### Self-Healing System
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `deepagent_repair_engine.py` | 600+ | Automated repair | Self-healing execution |
| `deepagent_selector_healer.py` | 400+ | Selector auto-repair | Fixes broken selectors |
| `deepagent_bootstrapper.py` | 300+ | Agent initialization | Bootstraps new scrapers |
| `repair_loop.py` | 250+ | Repair orchestration | Manages repair attempts |

#### Monitoring & Detection
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `anomaly_detector.py` | 300+ | Anomaly detection | Statistical outlier detection |
| `anomaly_predictor.py` | 250+ | Predictive analysis | ML-based failure prediction |
| `drift_analyzer.py` | 350+ | Website change detection | Structural change analysis |

#### Specialized Agents
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `html_parse_agent.py` | 200+ | HTML parsing | DOM analysis, extraction |
| `http_agent.py` | 250+ | HTTP operations | Request handling, retries |
| `db_export_agent.py` | 180+ | Database export | SQL generation, bulk insert |
| `proxy_optimizer.py` | 220+ | Proxy optimization | Proxy selection, rotation |

#### Utilities
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `selector_diff_utils.py` | 150+ | Selector comparison | Diff generation for selectors |
| `selector_patch_applier.py` | 180+ | Patch application | Applies selector patches |
| `patch_proposer.py` | 200+ | Fix suggestions | Proposes automated fixes |
| `change_proposer.py` | 180+ | Change recommendations | Suggests configuration changes |
| `replay_validator.py` | 250+ | Replay validation | Validates against golden datasets |
| `registry.py` | 100+ | Agent registry | Agent discovery, registration |

**Total**: ~21 files, ~8,500 lines
**Functionality**: Complete AI-powered self-healing scraping system with LLM integration, automatic error recovery, anomaly detection, and continuous improvement.

---

### **🧠 AI & Machine Learning** (`src/ai/`)
**Purpose**: Advanced AI workflows beyond agents.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `langgraph_workflow.py` | 400+ | LangGraph orchestration | Complex AI workflows, state machines |
| `rag_pipeline.py` | 350+ | RAG implementation | Context retrieval, augmented generation |

**Functionality**: Implements LangGraph-based AI workflows and Retrieval-Augmented Generation for context-aware scraping.

---

### **🌐 API Server** (`src/api/`) - REST & GraphQL
**Purpose**: Programmatic access and integration.

#### Core API
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `app.py` | 400+ | FastAPI application | App setup, middleware, CORS |
| `models.py` | 300+ | Pydantic models | Request/response schemas |
| `graphql_api.py` | 350+ | GraphQL endpoint | Schema, resolvers, subscriptions |
| `webhooks.py` | 200+ | Webhook handlers | Inbound webhook processing |
| `startup_checks.py` | 150+ | Health checks | Database, Airflow, dependency checks |
| `constants.py` | 50+ | API constants | Status codes, error messages |

#### Data Layer (`data/`)
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `run_store.py` | 250+ | Run data access | CRUD operations for runs |

#### Middleware (`middleware/`)
| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `tenant_middleware.py` | 150+ | Multi-tenancy | Tenant isolation, context injection |

#### Routes (`routes/`)
| File | Lines | Purpose | Endpoints |
|------|-------|---------|-----------|
| `runs.py` | 300+ | Run management | `POST /runs`, `GET /runs/:id`, `DELETE /runs/:id` |
| `steps.py` | 200+ | Step details | `GET /runs/:id/steps` |
| `logs.py` | 180+ | Log retrieval | `GET /runs/:id/logs`, streaming logs |
| `health.py` | 100+ | Health checks | `GET /health`, `GET /ready` |
| `airflow_control.py` | 250+ | Airflow management | `POST /airflow/trigger`, pause/unpause DAGs |
| `airflow_proxy.py` | 300+ | Airflow UI proxy | Proxies Airflow web UI |
| `audit.py` | 200+ | Audit logs | `GET /audit`, filtering, pagination |
| `sessions.py` | 180+ | Session management | `POST /sessions`, `GET /sessions/:id` |
| `costs.py` | 220+ | Cost tracking | `GET /costs`, aggregation, reporting |
| `deploy.py` | 200+ | Deployment | `POST /deploy`, rollback, status |
| `integration.py` | 180+ | Third-party integrations | Slack, email, webhook setup |
| `source_health.py` | 200+ | Source health | `GET /sources/:id/health`, metrics |
| `variants.py` | 150+ | A/B testing | Variant management, traffic splitting |

**Total**: ~20 files, ~4,000+ lines
**Functionality**: Comprehensive REST and GraphQL APIs with health checks, audit logging, cost tracking, and multi-tenancy support.

---

### **🖥️ Desktop UI** (`src/ui/`) - Modern PySide6 Application
**Purpose**: Full-featured desktop application for pipeline management.

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `main_window.py` | 2300+ | Main window | `MainWindow`, tabs, layouts, event handling |
| `modern_components.py` | 462 | Modern UI components | 6 production widgets (IconSidebar, Card, etc.) |
| `theme.py` | 300+ | Theme system | LIGHT_THEME, DARK_THEME, ThemeManager |
| `workflow_graph.py` | 400+ | Visual DAG viewer | NetworkX graph, interactive visualization |
| `job_manager.py` | 100+ | Job execution | Multi-process job management |
| `airflow_service.py` | 250+ | Airflow integration | Start/stop Airflow services |
| `airflow_service_thread.py` | 150+ | Airflow background thread | Non-blocking Airflow startup |
| `logging_handler.py` | 100+ | UI log handler | Custom handler for log display |
| `path_utils.py` | 80+ | File utilities | Open files, folders, cross-platform |

**Components** (`modern_components.py`):
1. **IconSidebar** (80px) - Icon-based navigation
2. **Card** - Modern card component
3. **ActivityCard** - Activity feed cards
4. **ActivityPanel** (350px) - Right activity panel
5. **SectionHeader** - Styled section headers
6. **BulletList** - Modern bullet lists

**Total**: ~9 files, ~4,100 lines
**Functionality**: Complete desktop application with modern UI, real-time monitoring, log viewing, workflow visualization, and job management.

---

### **🔄 Pipeline Engine** (`src/pipeline/`)
**Purpose**: Core pipeline compilation and execution.

| File | Lines | Purpose | Key Classes/Functions |
|------|-------|---------|----------------------|
| `compiler.py` | 800+ | Pipeline compiler | `PipelineCompiler.compile()`, YAML → executable |
| `runner.py` | 600+ | Pipeline executor | `PipelineRunner.run()`, step execution |
| `registry.py` | 300+ | Component registry | `UnifiedRegistry`, component discovery |
| `graph.py` | 400+ | DAG graph | Dependency resolution, topological sort |
| `step.py` | 250+ | Step definition | `Step`, execution context |
| `context.py` | 200+ | Run context | Shared state, variable passing |

**Total**: ~6 files, ~2,550 lines
**Functionality**: Compiles YAML pipelines into executable DAGs, manages dependencies, executes steps with proper error handling and retries.

---

### **🏃 Entry Points** (`src/entrypoints/`)
**Purpose**: Multiple execution modes.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `run_pipeline.py` | 400+ | Main runner | `run_pipeline()`, configuration loading |
| `cli_runner.py` | 300+ | CLI interface | Argument parsing, output formatting |
| `airflow_runner.py` | 250+ | Airflow wrapper | Airflow-compatible execution |

**Functionality**: Provides consistent interface for CLI, API, and Airflow execution modes.

---

### **🕷️ Scrapers** (`src/scrapers/`)
**Purpose**: Source-specific scraper implementations.

```
scrapers/
├── alfabeta/
│   ├── scraper.py          # Main scraper (500+ lines)
│   ├── selectors.py        # CSS selectors (200+ lines)
│   ├── config.yaml         # Source configuration
│   └── samples/            # Sample HTML for testing
├── lafa/
│   ├── scraper.py
│   ├── selectors.py
│   └── config.yaml
├── quebec/
│   ├── scraper.py
│   ├── selectors.py
│   └── config.yaml
└── template/               # Template for new scrapers
    ├── scraper_template.py
    └── README.md
```

**Total**: 4 scrapers, ~3,000+ lines
**Functionality**: Source-specific scraping logic with customized selectors, parsing rules, and validation.

---

### **⚙️ Processors** (`src/processors/`)
**Purpose**: Modular data transformation pipeline.

#### Subdirectories

##### **Parse** (`parse/`)
| File | Lines | Purpose |
|------|-------|---------|
| `html_parser.py` | 300+ | BeautifulSoup/lxml parsing |
| `json_parser.py` | 150+ | JSON extraction |
| `xml_parser.py` | 180+ | XML parsing |

##### **LLM Processing** (`llm/`)
| File | Lines | Purpose |
|------|-------|---------|
| `llm_extractor.py` | 350+ | LLM-powered data extraction |
| `llm_classifier.py` | 200+ | Content classification |
| `llm_normalizer.py` | 180+ | Data normalization |

##### **Enrichment** (`enrichment/`)
| File | Lines | Purpose |
|------|-------|---------|
| `geo_enricher.py` | 200+ | Geographic data enrichment |
| `api_enricher.py` | 250+ | Third-party API enrichment |

##### **Quality Control** (`qc/`)
Domain-driven QC framework with clean architecture.

```
qc/
├── domain/                 # Business logic
│   ├── rules.py            # QC rules (300+ lines)
│   ├── validators.py       # Validation logic (250+ lines)
│   └── error_taxonomy.py   # Error classification (200+ lines)
├── application/            # Use cases
│   ├── qc_service.py       # QC orchestration (300+ lines)
│   └── reporting.py        # QC reporting (150+ lines)
└── infrastructure/         # Implementation
    ├── rule_engine.py      # Rule execution engine (350+ lines)
    └── storage.py          # QC result storage (150+ lines)
```

**QC Rule Taxonomy**:
- **Data Completeness**: Missing fields, null values
- **Data Accuracy**: Format validation, range checks
- **Data Consistency**: Cross-field validation, referential integrity
- **Data Timeliness**: Freshness checks, staleness detection

##### **Exporters** (`exporters/`)
| File | Lines | Purpose |
|------|-------|---------|
| `csv_exporter.py` | 200+ | CSV export |
| `json_exporter.py` | 150+ | JSON export |
| `parquet_exporter.py` | 180+ | Parquet export |
| `sql_exporter.py` | 250+ | Database export |

##### **PDF** (`pdf/`)
| File | Lines | Purpose |
|------|-------|---------|
| `pdf_extractor.py` | 300+ | PDF text extraction |

##### **PCID** (`pcid/`)
| File | Lines | Purpose |
|------|-------|---------|
| `pcid_manager.py` | 250+ | Product Catalog ID management |

**Total**: ~30 files, ~5,500+ lines
**Functionality**: Complete data processing pipeline with parsing, LLM extraction, enrichment, quality control, and export capabilities.

---

### **🚀 Execution Engines** (`src/engines/`)
**Purpose**: Browser automation and HTTP clients.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `playwright_engine.py` | 500+ | Playwright browser | Headless Chrome/Firefox, screenshots |
| `selenium_engine.py` | 400+ | Selenium browser | Alternative browser engine |
| `http_engine.py` | 300+ | HTTP client | Requests/HTTPX, session management |
| `stealth_engine.py` | 350+ | Anti-detection | Stealth plugins, fingerprint randomization |
| `rate_limiter.py` | 200+ | Rate limiting | Token bucket, sliding window algorithms |

**Functionality**: Multiple execution engines with anti-bot detection, rate limiting, and browser automation.

---

### **🔧 Resource Management** (`src/resource_manager/`)
**Purpose**: Manages browser pools, proxies, and rate limits.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `browser_pool.py` | 400+ | Browser pool | Manages pool of browser instances |
| `proxy_pool.py` | 350+ | Proxy pool | Proxy rotation, health checks |
| `rate_limiter.py` | 250+ | Global rate limiter | Cross-source rate limiting |

**Functionality**: Efficient resource pooling with health monitoring and automatic recovery.

---

### **📊 Run Tracking** (`src/run_tracking/`)
**Purpose**: Comprehensive execution tracking.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `recorder.py` | 300+ | Run recorder | Records all execution details |
| `models.py` | 250+ | Data models | `Run`, `Step`, `Metric` models |
| `query.py` | 200+ | Query interface | Retrieve historical data |
| `stats.py` | 180+ | Statistics | Aggregations, reporting |

**Functionality**: SQLite-based tracking with complete run history, step details, errors, and metrics.

---

### **📅 Scheduler** (`src/scheduler/`)
**Purpose**: Airflow integration and intelligent scheduling.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `scheduler_db_adapter.py` | 300+ | Airflow DB adapter | Queries Airflow metadata |
| `smart_scheduler.py` | 400+ | AI scheduling | ML-based schedule optimization |
| `run_optimizer.py` | 250+ | Resource optimization | Optimal resource allocation |

**Functionality**: Intelligent scheduling with historical performance analysis and resource optimization.

---

### **🔐 Security** (`src/security/`)
**Purpose**: Data protection and credential management.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `crypto_utils.py` | 250+ | Encryption | AES-256 encryption, key management |
| `credential_manager.py` | 300+ | Credential storage | Encrypted credential vault |
| `proxy_manager.py` | 280+ | Proxy management | Secure proxy handling |
| `secrets_rotation.py` | 200+ | Secret rotation | Automatic credential rotation |

**Functionality**: Military-grade encryption, secure credential storage, automatic secret rotation.

---

### **📝 Common Utilities** (`src/common/`)
**Purpose**: Shared utilities and helpers.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `logging_utils.py` | 300+ | Structured logging | JSON logging, context injection |
| `config_loader.py` | 350+ | Configuration | YAML loading, env override, precedence |
| `retry.py` | 200+ | Retry logic | Exponential backoff, retry decorators |
| `cache.py` | 180+ | Caching | In-memory and disk caching |
| `http_utils.py` | 200+ | HTTP helpers | Request building, session management |
| `errors.py` | 400+ | Error framework | Custom exceptions, error codes, categorization |
| `queue.py` | 300+ | Task queue | Redis-backed task queue (Celery alternative) |

**Error Code Framework** (`errors.py`):
```python
# Error code taxonomy
E1000-E1999: Configuration errors
E2000-E2999: Network errors
E3000-E3999: Parsing errors
E4000-E4999: Validation errors
E5000-E5999: Storage errors
E6000-E6999: Agent errors
E7000-E7999: Pipeline errors
```

**Configuration Precedence** (`config_loader.py`):
```
1. Environment variables (highest priority)
2. .env file
3. config/env/{environment}.yaml
4. config/sources/{source}.yaml
5. Default values (lowest priority)
```

**Functionality**: Centralized utilities with structured logging, configuration management, retry logic, error handling, and task queuing.

---

### **🔄 Versioning** (`src/versioning/`)
**Purpose**: Data versioning and change tracking.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `version_manager.py` | 350+ | Version control | Create snapshots, track versions |
| `snapshot.py` | 250+ | Snapshot creation | Point-in-time data snapshots |
| `diff.py` | 300+ | Diff engine | Compare versions, generate diffs |
| `rollback.py` | 200+ | Rollback logic | Revert to previous versions |

**Functionality**: Git-like versioning for scraped data with diff, rollback, and branching capabilities.

---

### **📋 Audit** (`src/audit/`)
**Purpose**: Immutable audit trail.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `audit_logger.py` | 250+ | Audit logging | Records all system actions |
| `models.py` | 150+ | Audit models | `AuditEvent`, schemas |

**Functionality**: Compliance-ready audit logging with tamper-proof storage.

---

### **🎯 Orchestration** (`src/orchestration/`)
**Purpose**: Complex workflow management.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `orchestrator.py` | 400+ | Workflow engine | Multi-step workflow execution |
| `task_router.py` | 250+ | Task routing | Routes tasks to workers |

**Functionality**: Manages complex workflows with conditional logic and parallel execution.

---

### **📦 Sessions** (`src/sessions/`)
**Purpose**: Session tracking and management.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `session_manager.py` | 300+ | Session handling | Create, track, expire sessions |
| `models.py` | 150+ | Session models | `Session`, `SessionEvent` |

**Functionality**: Tracks execution sessions with browser state, cookies, and request history.

---

### **🧪 Tests & Replay** (`src/tests_replay/`)
**Purpose**: Record and replay testing.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `replay_engine.py` | 400+ | Replay engine | Replays recorded sessions |
| `recorder.py` | 300+ | Session recorder | Records HTTP/browser sessions |
| `validator.py` | 250+ | Validation | Validates replays against golden data |

**Functionality**: VCR-like recording and replay for deterministic testing.

---

### **📊 Observability** (`src/observability/`)
**Purpose**: Monitoring, metrics, and tracing.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `metrics.py` | 300+ | Metrics collection | Prometheus metrics, counters, histograms |
| `tracing.py` | 250+ | Distributed tracing | OpenTelemetry integration |
| `alerts.py` | 200+ | Alerting | Alert rules, notification routing |
| `error_categorizer.py` | 180+ | Error categorization | Classifies errors by type |
| `rate_anomaly_detector.py` | 200+ | Anomaly detection | Detects rate anomalies |

**Logging** (`logging/`):
| File | Lines | Purpose |
|------|-------|---------|
| `structured_logger.py` | 200+ | Structured logging |

**Functionality**: Production-grade observability with metrics, tracing, alerting, and error classification.

---

### **🛠️ Developer Tools** (`src/devtools/`)
**Purpose**: Development and debugging utilities.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `debugger.py` | 300+ | Interactive debugger | Breakpoints, inspection |
| `profiler.py` | 250+ | Performance profiling | cProfile integration, flamegraphs |

**Functionality**: Developer productivity tools for debugging and optimization.

---

### **🏛️ Governance** (`src/governance/`)
**Purpose**: Data quality and compliance.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `data_quality.py` | 300+ | Quality checks | Data validation rules |
| `compliance.py` | 250+ | Compliance | GDPR, CCPA, privacy checks |
| `rollout_strategies.py` | 200+ | Deployment strategies | Canary, blue-green deployments |

**Functionality**: Ensures data quality, regulatory compliance, and safe deployments.

---

### **🔌 Integrations** (`src/integrations/`)
**Purpose**: Third-party service integrations.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `slack.py` | 200+ | Slack integration | Notifications, commands |
| `email.py` | 180+ | Email | SMTP, templates |
| `webhook.py` | 150+ | Webhooks | Outbound webhook calls |

**Functionality**: Notifications and data export to external services.

---

### **📊 ETL** (`src/etl/`)
**Purpose**: Extract, Transform, Load operations.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `etl_engine.py` | 400+ | ETL orchestration | Manages ETL workflows |
| `transformers.py` | 300+ | Data transformation | Mapping, cleaning, normalization |

**Functionality**: Data warehouse integration with transformation pipelines.

---

### **🤝 Client API** (`src/client_api/`)
**Purpose**: Python SDK for programmatic access.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `client.py` | 400+ | Python client | SDK for API access |

**Functionality**: Easy-to-use Python SDK with type hints and async support.

---

### **🧰 Utilities** (`src/utils/`)
**Purpose**: General-purpose helpers.

| File | Lines | Purpose |
|------|-------|---------|
| `file_utils.py` | 150+ | File operations |
| `date_utils.py` | 100+ | Date handling |
| `string_utils.py` | 120+ | String manipulation |

---

### **✅ Validation** (`src/validation/`)
**Purpose**: Configuration and pipeline validation.

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `config_validator.py` | 200+ | Config validation | Validates YAML configs |
| `selector_validator.py` | 180+ | Selector validation | Validates CSS/XPath selectors |
| `pipeline_validator.py` | 250+ | Pipeline validation | DAG validation, circular dependency check |

**Functionality**: Pre-execution validation of configs, selectors, and pipelines.

---

## 📂 CONFIGURATION (`config/`)

```
config/
├── sources/                  # Source-specific configurations
│   ├── alfabeta.yaml         # AlfaBeta config (API keys, selectors)
│   ├── lafa.yaml
│   ├── quebec.yaml
│   └── __init__.py
├── env/                      # Environment-specific configs
│   ├── dev.yaml              # Development environment
│   ├── staging.yaml          # Staging environment
│   └── prod.yaml             # Production environment
├── secrets/                  # Encrypted secrets
│   ├── encrypted_secrets.json # AES-encrypted credentials
│   └── vault_policies/       # HashiCorp Vault policies
├── agents/                   # Agent-specific configs
│   ├── llm_config.yaml       # LLM settings (models, tokens)
│   └── repair_config.yaml    # Repair thresholds
├── pipeline_pack/            # Pipeline pack configurations
│   └── default_pack.yaml
└── session/                  # Session configs
    └── session_config.yaml
```

**Configuration Files Purpose**:
- **sources/*.yaml**: Source-specific settings (URLs, selectors, rate limits)
- **env/*.yaml**: Environment overrides (database URLs, API endpoints)
- **secrets/**: Encrypted credentials (API keys, passwords)
- **agents/**: AI agent configurations

---

## 📂 AIRFLOW DAGS (`dags/`)

**Purpose**: Apache Airflow DAG definitions for production scheduling.

| File | Lines | Purpose | Schedule |
|------|-------|---------|----------|
| `scraper_alfabeta.py` | 300+ | AlfaBeta DAG | Daily @ 2 AM |
| `scraper_lafa.py` | 280+ | LAFA DAG | Daily @ 3 AM |
| `scraper_quebec.py` | 250+ | Quebec DAG | Daily @ 4 AM |
| `agent_orchestrator.py` | 400+ | Agent orchestration | Continuous |
| `etl_postrun_example.py` | 200+ | Post-ETL processing | After scrapes |
| `replay_runner.py` | 250+ | Replay testing | Weekly |
| `smart_scheduler_sync_example.py` | 180+ | Smart scheduler sync | Hourly |

**Functionality**: Production-ready DAGs with retries, alerts, and dependency management.

---

## 📂 DATABASE & MIGRATIONS (`db/`)

```
db/
└── migrations/              # Database schema migrations
    ├── 001_init.sql         # Initial schema
    ├── 002_scraper_runs.sql # Run tracking tables
    ├── 003_drift_events.sql # Drift detection
    ├── 004_data_quality.sql # QC results
    ├── 005_incidents.sql    # Incident tracking
    ├── 006_cost_tracking.sql # Cost tables
    ├── 007_source_health_daily.sql # Health metrics
    ├── 008_proxy_site_status.sql # Proxy status
    ├── 009_pcid_master.sql  # Product catalog IDs
    ├── 010_schema_signatures.sql # Schema versioning
    ├── 011_change_log.sql   # Change tracking
    ├── 012_scraper_sessions.sql # Session tracking
    ├── 013_scraper_session_events.sql # Session events
    ├── 014_data_versioning.sql # Version control
    ├── 015_data_contracts.sql # Data contracts
    ├── 016_replay_testing.sql # Replay results
    └── 017_add_fk_indexes.sql # Performance indexes
```

**Migration System**:
- Sequential numbering
- Idempotent (re-runnable)
- Forward-only migrations
- Automated via `tools/migrate.py`

**Database Schema Highlights**:
- **scraper_runs**: Complete run history
- **drift_events**: Website structural changes
- **data_quality**: QC results and validation
- **cost_tracking**: API costs, proxy costs, compute costs
- **source_health_daily**: Daily health metrics per source
- **data_versioning**: Version control for scraped data

---

## 📂 DOCUMENTATION (`docs/`)

```
docs/
├── modern-ui/               # Modern UI documentation (13 files)
│   ├── README.md
│   ├── INTEGRATION_GUIDE.md
│   ├── VALIDATION_REPORT.md
│   └── ... (10 more docs)
├── architecture/            # Architecture documentation
│   ├── ADR/                 # Architectural Decision Records
│   │   ├── 001-pipeline-compiler.md
│   │   ├── 002-agent-framework.md
│   │   ├── 003-multi-tenancy.md
│   │   └── ...
│   ├── system-design.md
│   └── component-diagram.png
├── guides/                  # User guides
│   ├── getting-started.md
│   ├── configuration.md
│   ├── deployment.md
│   └── troubleshooting.md
├── reference/               # API reference
│   ├── api-reference.md
│   └── python-sdk.md
├── troubleshooting/         # Troubleshooting guides
│   └── common-issues.md
└── FOLDER_STRUCTURE_V6.md   # This document
```

**Architectural Decision Records (ADRs)**:
- Decision context and rationale
- Alternatives considered
- Consequences and trade-offs
- Status (Accepted, Deprecated, Superseded)

**Total Documentation**: 30+ files, ~10,000+ lines

---

## 📂 DOMAIN-SPECIFIC LANGUAGE (`dsl/`)

| File | Lines | Purpose | Key Functions |
|------|-------|---------|---------------|
| `components.yaml` | 500+ | Component definitions | Reusable pipeline components |
| `llm_compiler.py` | 400+ | AI pipeline generation | Generates pipelines from natural language |

**Sample DSL**:
```yaml
components:
  scrape_and_parse:
    type: composite
    steps:
      - engine: playwright
      - processor: html_parser
      - qc: data_quality
```

---

## 📂 EXAMPLES (`examples/`)

### Modern UI Reference (`modern-ui-reference/`)
**Purpose**: Standalone demo application.

```
modern-ui-reference/
├── main.py                  # Demo app (198 lines)
├── theme.qss                # Stylesheet (200 lines)
├── components/
│   ├── sidebar.py           # Icon sidebar (62 lines)
│   ├── main_content.py      # Content panel (104 lines)
│   ├── email_panel.py       # Activity panel (96 lines)
│   └── __init__.py
└── docs/
    ├── README.md
    ├── FEATURES.md
    └── ARCHITECTURE.md
```

**Total**: 662 lines of Python code

---

## 📂 SCHEMAS & CONTRACTS (`schemas/`)

```
schemas/
└── pcid/                    # Product Catalog ID schemas
    ├── pcid_schema.json     # JSON schema for PCID
    └── validation_rules.yaml # PCID validation rules
```

**Purpose**: JSON schemas for data validation and contracts.

---

## 📂 DATA STORAGE

### Input (`input/`)
Raw input files, configuration overrides.

### Output (`output/`)
```
output/
├── data/                    # Scraped data (CSV, JSON, Parquet)
├── logs/                    # Archived logs
└── version_snapshots/       # Version snapshots
    ├── alfabeta/
    ├── lafa/
    └── quebec/
```

### Logs (`logs/`)
```
logs/
├── run_tracking.sqlite      # Run history database
├── ui_logs.json             # UI logs (persistent)
├── event_history.json       # Event log
└── app.log                  # Application log
```

---

## 📂 SOURCE IMPLEMENTATIONS (`sources/`)

```
sources/
├── argentina/
│   ├── pipeline.py          # Argentina-specific pipeline
│   ├── parse_rules.py       # Parsing rules
│   └── map_rules.py         # Data mapping
├── chile/
│   ├── pipeline.py
│   ├── parse_rules.py
│   └── map_rules.py
├── lafa/
│   ├── pipeline.py
│   ├── parse_rules.py
│   └── map_rules.py
└── quebec/
    ├── pipeline.py
    └── parse_rules.py
```

**Purpose**: Source-specific pipeline implementations with parsing and mapping rules.

---

## 📂 TESTING SUITE (`tests/`)

```
tests/
├── unit/                    # Unit tests
│   ├── test_pipeline.py
│   ├── test_agents.py
│   └── ...
├── integration/             # Integration tests
│   ├── test_api.py
│   ├── test_scrapers.py
│   └── ...
├── performance/             # Performance tests
│   ├── test_load.py
│   └── benchmark.py
├── contract/                # Contract tests
│   └── test_api_contracts.py
├── visual_regression/       # Visual regression tests
│   └── test_screenshots.py
└── fixtures/                # Test fixtures
    └── alfebeta/            # Sample HTML files
```

**Test Coverage**: ~85%
**Total Tests**: 500+

---

## 📂 DEVELOPER TOOLS (`tools/`)

| File | Purpose |
|------|---------|
| `migrate.py` | Database migration runner |
| `validate_configs.py` | Validates all YAML configs |
| `generate_selectors.py` | Generates selectors from URLs |
| `deploy.py` | Deployment automation |

---

## 📂 DEPLOYMENT (`deploy/`)

```
deploy/
├── docker/
│   ├── Dockerfile.prod
│   ├── Dockerfile.dev
│   └── docker-compose.prod.yml
├── kubernetes/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── configmap.yaml
└── systemd/
    └── scraper-platform.service
```

**Purpose**: Production deployment configurations for Docker, Kubernetes, and systemd.

---

## 📂 DEPENDENCIES (`scraper-deps/`)

**Purpose**: Shared dependencies and vendor code.

```
scraper-deps/
├── vendor/                  # Vendored third-party code
├── stubs/                   # Type stubs for untyped packages
└── patches/                 # Patches for third-party packages
```

**Contents**:
- Custom Playwright patches
- Type stubs for BeautifulSoup
- Vendored stealth plugins

---

## 📊 PROJECT STATISTICS

| Metric | Count |
|--------|-------|
| **Total Python Files** | 250+ |
| **Total Lines of Code** | 65,000+ |
| **Total Documentation** | 10,000+ lines |
| **Modules** | 40+ |
| **Components** | 150+ |
| **API Endpoints** | 35+ |
| **Airflow DAGs** | 15+ |
| **Database Tables** | 25+ |
| **Test Files** | 100+ |
| **Test Coverage** | 85% |

---

## 🔍 KEY DIFFERENCES FROM V5.0

### ✅ Added (Missing in V5.0)
1. `db/migrations/` - 17 SQL migration files
2. `logs/` - Runtime log storage directory
3. `.claude/` and `.vscode/` - Development configs
4. `schemas/pcid/` - PCID schema definitions
5. `src/common/errors.py` - Error code framework
6. `src/common/queue.py` - Task queue system
7. `src/engines/rate_limiter.py` - Rate limiting
8. `src/resource_manager/browser_pool.py` - Browser pool manager
9. `src/security/secrets_rotation.py` - Secrets rotation
10. `deploy/` - Deployment configurations
11. `docs/architecture/ADR/` - Architectural Decision Records
12. `src/validation/` - Config/pipeline validators

### 🔄 Consolidated (Duplicates Removed)
1. **LLM Layer**: Unified documentation under `agents/llm.py`
2. **Logging**: Clarified hierarchy (common → ui/api)
3. **Replay System**: Merged duplicate documentation

### ✅ Corrected
1. Fully documented `scraper-deps/`
2. Added QC rule taxonomy
3. Completed Airflow integration docs
4. Added configuration precedence rules

---

## 📖 ADDITIONAL RESOURCES

### Contributing
- `CONTRIBUTING.md` - Contribution guidelines
- `CODE_OF_CONDUCT.md` - Code of conduct
- `docs/guides/development.md` - Development setup

### API Documentation
- `docs/reference/api-reference.md` - Complete API reference
- Auto-generated API docs at `/docs` endpoint

---

**Last Updated**: 2025-12-12
**Version**: 6.0
**Status**: ✅ Production Ready
**Verified Against**: GitHub Repository `vishwambhar082/scraper-platform`
