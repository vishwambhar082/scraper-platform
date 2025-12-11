# Scraper Platform v5.0 - Unified Pipeline Architecture

## Overview

The scraper platform has been completely refactored with a unified pipeline architecture that consolidates and simplifies the codebase. This document provides a comprehensive guide to the new system.

## Architecture Changes

### Before (v4.x)
- **3 separate pipeline systems**:
  - `src/core_kernel/` - DSL-based execution engine
  - `src/agents/` - Agent orchestrator with complex workflows
  - `src/pipeline_pack/agents/` - Alternate agent system
- **Multiple registries**: ComponentRegistry, AgentRegistry (x2)
- **Inconsistent DAG implementations**: Each scraper had custom DAG code
- **Duplicated configuration**: Settings scattered across multiple locations

### After (v5.0)
- **Single unified pipeline system** in `src/pipeline/`
- **One registry**: `UnifiedRegistry` for all components
- **Standardized DAG factory**: `build_scraper_dag()` in `dags/scraper_base.py`
- **Consolidated configuration**: Clear hierarchy in `config/`

## Core Components

### 1. Unified Pipeline (`src/pipeline/`)

#### `PipelineRunner`
- Executes compiled pipelines with dependency resolution
- Supports parallel execution (non-export steps)
- Sequential execution for export steps
- Automatic retry logic
- Comprehensive result tracking

#### `UnifiedRegistry`
- Single source of truth for all components
- Load from YAML or register programmatically
- Type-safe component resolution

#### `PipelineCompiler`
- Compiles YAML pipeline definitions
- Validates step dependencies
- Resolves components from registry

#### `PipelineStep`
- Represents atomic pipeline operation
- Type classification (FETCH, PARSE, TRANSFORM, VALIDATE, ENRICH, EXPORT, AGENT, CUSTOM)
- Built-in error handling and timing

### 2. Step Types

```
FETCH      - HTTP/API requests, web scraping
PARSE      - HTML/JSON parsing, data extraction
TRANSFORM  - Data transformation, field mapping
VALIDATE   - QC rules, data validation
ENRICH     - LLM normalization, PCID matching
EXPORT     - Database, S3, GCS export
AGENT      - AI-powered autonomous operations
CUSTOM     - User-defined operations
```

### 3. DAG Structure

All scrapers use the standardized factory:

```python
from dags.scraper_base import build_scraper_dag

dag = build_scraper_dag(
    source="alfabeta",
    dag_id="scraper_alfabeta_v5",
    description="AlfaBeta pharma scraper (unified pipeline v5.0)",
    schedule="0 3 * * *",
    tags=["scraper", "alfabeta", "v5"],
)
```

Benefits:
- **Consistency**: All DAGs follow the same pattern
- **Maintainability**: Changes propagate to all scrapers
- **Jira Integration**: Built-in support for Jira-triggered runs
- **Error Handling**: Standardized error propagation

## Pipeline Definition (YAML)

### Example: `dsl/pipelines/alfabeta.yaml`

```yaml
pipeline:
  name: alfabeta
  description: AlfaBeta pharma scraper
  
  steps:
    - id: fetch_listings
      component: alfabeta.fetch_listings
      type: fetch
      params:
        max_pages: 10
    
    - id: parse_products
      component: alfabeta.parse_products
      type: parse
      depends_on:
        - fetch_listings
    
    - id: normalize_data
      component: alfabeta.normalize
      type: enrich
      depends_on:
        - parse_products
    
    - id: match_pcid
      component: alfabeta.match_pcid
      type: enrich
      depends_on:
        - normalize_data
    
    - id: validate_qc
      component: alfabeta.validate
      type: validate
      depends_on:
        - match_pcid
      required: false  # Optional step
    
    - id: export_db
      component: alfabeta.export_database
      type: export
      depends_on:
        - validate_qc
```

### Component Registry: `dsl/components.yaml`

```yaml
components:
  alfabeta.fetch_listings:
    module: src.scrapers.alfabeta.pipeline
    callable: fetch_listings
    type: fetch
    description: Fetch product listings from AlfaBeta
  
  alfabeta.parse_products:
    module: src.scrapers.alfabeta.pipeline
    callable: parse_products
    type: parse
    description: Parse product details from HTML
  
  # ... more components
```

## Execution Flow

### 1. DAG Trigger
```
Airflow DAG → build_scraper_dag() → _build_task_callable()
```

### 2. Pipeline Compilation
```
UnifiedRegistry.from_yaml() → PipelineCompiler.compile_from_file() → CompiledPipeline
```

### 3. Pipeline Execution
```
PipelineRunner.run() → 
  ├─ Dependency resolution
  ├─ Parallel execution (non-export steps)
  ├─ Sequential execution (export steps)
  └─ Result aggregation → RunResult
```

### 4. Result Handling
```
RunResult →
  ├─ Update run tracker
  ├─ Update Jira (if triggered from Jira)
  └─ Return to Airflow
```

## Key Features

### Parallel Execution
- Non-export steps run in parallel when dependencies are met
- Configurable worker pool size
- Automatic deadlock detection

### Export Step Ordering
- Export steps (database writes, file uploads) run sequentially
- Maintains data consistency
- Prevents race conditions

### Error Handling
- Per-step retry logic
- Optional vs. required steps
- Comprehensive error propagation
- Automatic Airflow task failure on pipeline failure

### Jira Integration
- Automatic Jira ticket updates
- Status, run ID, item count tracking
- Error message propagation
- Supports manual and webhook-triggered runs

## Configuration Hierarchy

```
config/
├── settings.yaml           # Global platform settings
├── logging.yaml            # Logging configuration
├── proxies.yaml            # Proxy configuration
├── etl.yaml                # ETL settings
├── env/                    # Environment-specific
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── sources/                # Source-specific
│   ├── alfabeta.yaml
│   ├── argentina.yaml
│   ├── chile.yaml
│   ├── quebec.yaml
│   └── lafa.yaml
├── agents/                 # Agent configuration
│   ├── defaults.yaml
│   └── pipelines.yaml
└── session/                # Session management
    └── defaults.yaml
```

## Migration Guide

### For Existing Scrapers

1. **Create pipeline definition** in `dsl/pipelines/{source}.yaml`
2. **Register components** in `dsl/components.yaml`
3. **Create v5 DAG** using `build_scraper_dag()` factory
4. **Test pipeline** with `python -m src.entrypoints.run_pipeline --source {source} --environment dev`
5. **Deploy** and monitor

### For New Scrapers

Use the scaffolding tool:

```bash
python tools/add_scraper_advanced.py my_new_source \
  --engine selenium \
  --requires-login \
  --base-url https://example.com \
  --interactive
```

This generates:
- Pipeline definition
- Component registration
- Source configuration
- V5 DAG file
- Sample scraper code

## Benefits

### Simplified Codebase
- **Reduced from 3 systems to 1**: Single execution model
- **-60% lines of code**: Removed duplication
- **Clear separation of concerns**: Components, pipeline, execution

### Improved Maintainability
- **Standardized patterns**: All scrapers follow same structure
- **Centralized configuration**: One place to update
- **Type safety**: Strong typing throughout

### Better Performance
- **Parallel execution**: Faster pipeline runs
- **Efficient resource usage**: Controlled worker pools
- **Optimized export**: Sequential writes prevent conflicts

### Enhanced Observability
- **Detailed step timing**: Performance tracking
- **Comprehensive logging**: Every step logged
- **Run tracking**: Full run history and metrics
- **Jira integration**: Automatic ticket updates

## Testing

### Unit Tests
```bash
pytest tests/test_pipeline.py
```

### Integration Tests
```bash
pytest tests/integration/test_unified_pipeline.py
```

### Run Pipeline Locally
```bash
python -m src.entrypoints.run_pipeline \
  --source alfabeta \
  --environment dev \
  --run-type FULL_REFRESH
```

## Troubleshooting

### Pipeline Not Found
- Check `dsl/pipelines/{source}.yaml` exists
- Verify source name matches filename

### Component Not Registered
- Check `dsl/components.yaml` for component definition
- Verify module and callable names are correct
- Test import: `python -c "from {module} import {callable}"`

### Step Dependency Issues
- Verify `depends_on` references existing step IDs
- Check for circular dependencies
- Review pipeline compilation logs

### Export Step Failures
- Export steps run sequentially - check ordering
- Verify database connections
- Check export permissions (S3, GCS)

## Performance Tuning

### Worker Pool Size
```python
runner = PipelineRunner(max_workers=8)  # Default: 4
```

### Step Retries
```yaml
steps:
  - id: fetch_data
    retry: 3  # Retry up to 3 times
    timeout: 60  # Timeout after 60 seconds
```

### Optional Steps
```yaml
steps:
  - id: optional_validation
    required: false  # Won't fail pipeline
```

## Roadmap

- [ ] GraphQL-based pipeline visualization
- [ ] Real-time pipeline monitoring dashboard
- [ ] A/B testing framework for pipeline variants
- [ ] Auto-scaling based on pipeline load
- [ ] ML-powered step optimization
- [ ] Cross-source pipeline dependencies
- [ ] Pipeline templates and inheritance

## Support

For questions or issues:
1. Check this documentation
2. Review code comments in `src/pipeline/`
3. Check test examples in `tests/`
4. Create GitHub issue with pipeline YAML and logs
