# Workflow Diagram - Scraper Platform

## End-to-End Pipeline Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE EXECUTION WORKFLOW                  │
└─────────────────────────────────────────────────────────────────┘

1. INITIALIZATION
   │
   ├─ Load Configuration (YAML)
   │  ├─ config/settings.yaml
   │  ├─ config/env/{env}.yaml
   │  └─ config/sources/{source}.yaml
   │
   ├─ Load DSL Components
   │  └─ dsl/components.yaml
   │
   └─ Load Pipeline Definition
      └─ dsl/pipelines/{source}.yaml

2. REGISTRATION & COMPILATION
   │
   ├─ UnifiedRegistry.from_yaml()
   │  └─ Register all components
   │
   ├─ PipelineCompiler.compile_from_file()
   │  ├─ Resolve component references
   │  ├─ Build dependency graph
   │  └─ Create CompiledPipeline
   │
   └─ Validate dependencies
      └─ Check for circular dependencies

3. EXECUTION
   │
   ├─ PipelineRunner.run()
   │  │
   │  ├─ Generate Run ID
   │  │
   │  ├─ Create RunContext
   │  │  ├─ run_id
   │  │  ├─ source
   │  │  ├─ environment
   │  │  ├─ run_type
   │  │  └─ params
   │  │
   │  └─ Execute Pipeline Steps
   │     │
   │     ├─ Build Dependency Graph
   │     │  ├─ step_map: {step_id → PipelineStep}
   │     │  └─ dependents: {step_id → [dependent_steps]}
   │     │
   │     ├─ Categorize Steps
   │     │  ├─ Export steps (sequential)
   │     │  └─ Other steps (parallel)
   │     │
   │     └─ Execute with ThreadPoolExecutor
   │        │
   │        ├─ Ready Queue (no dependencies)
   │        │  └─ Submit to executor
   │        │
   │        ├─ Pending Queue (has dependencies)
   │        │  └─ Wait for dependencies
   │        │
   │        └─ Running Steps
   │           │
   │           ├─ For each step:
   │           │  ├─ Resolve component callable
   │           │  ├─ Prepare step inputs
   │           │  │  └─ Get outputs from dependencies
   │           │  ├─ Execute step
   │           │  │  └─ Call component with params
   │           │  ├─ Capture output
   │           │  └─ Store StepResult
   │           │
   │           └─ On completion:
   │              ├─ Mark step as complete
   │              ├─ Check dependents
   │              └─ Move ready dependents to ready queue
   │
   │     └─ Determine Final Status
   │        ├─ success: All steps succeeded
   │        ├─ partial: Some steps failed
   │        └─ failed: Critical steps failed

4. RECORDING & TRACKING
   │
   ├─ RunRecorder.start_run()
   │  └─ Record run metadata
   │
   ├─ Log step execution
   │  └─ UnifiedLogger.log()
   │
   └─ RunRecorder.finish_run()
      └─ Record final status and results

5. EXPORT & NOTIFICATION
   │
   ├─ Export Results
   │  ├─ Database export
   │  ├─ File export (CSV/JSON)
   │  └─ API webhook
   │
   ├─ Update Jira (if issue_key provided)
   │  └─ jira_airflow_integration
   │
   └─ Notify completion
      └─ Notifications service

┌─────────────────────────────────────────────────────────────────┐
│                    STEP EXECUTION DETAIL                        │
└─────────────────────────────────────────────────────────────────┘

PipelineStep Execution:
  │
  ├─ Input Preparation
  │  ├─ Get dependency outputs
  │  ├─ Merge runtime params
  │  └─ Validate inputs
  │
  ├─ Component Resolution
  │  ├─ UnifiedRegistry.resolve(component_name)
  │  └─ Load callable
  │
  ├─ Execution
  │  └─ callable(**prepared_params)
  │
  └─ Result Capture
     ├─ Success → StepResult(output, status="success")
     └─ Failure → StepResult(error, status="failed")

┌─────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY RESOLUTION                        │
└─────────────────────────────────────────────────────────────────┘

Topological Sort Algorithm:
  1. Build in-degree map for each step
  2. Start with steps having in-degree = 0
  3. Execute ready steps in parallel
  4. On completion, decrement dependents' in-degree
  5. Move newly ready steps to ready queue
  6. Repeat until all steps complete

Example:
  Step A (no deps) → ready
  Step B (depends on A) → pending
  Step C (depends on A) → pending
  Step D (depends on B, C) → pending

  Execution order:
  1. Execute A (parallel)
  2. On A complete → B, C become ready
  3. Execute B, C (parallel)
  4. On B, C complete → D becomes ready
  5. Execute D

┌─────────────────────────────────────────────────────────────────┐
│                    AIRFLOW INTEGRATION                          │
└─────────────────────────────────────────────────────────────────┘

Airflow DAG → PythonOperator
  │
  └─ Calls run_pipeline()
     │
     ├─ Extract DAG run context
     │  ├─ dag_run_id
     │  └─ conf parameters
     │
     ├─ Execute pipeline (same flow as above)
     │
     └─ Update Jira on completion
        └─ jira_airflow_integration.update_jira_on_completion()

┌─────────────────────────────────────────────────────────────────┐
│                    UI INTEGRATION                               │
└─────────────────────────────────────────────────────────────────┘

Desktop UI → PipelineRunnerThread (QThread)
  │
  ├─ Runs pipeline in background
  │
  ├─ Emits signals:
  │  ├─ log_message(level, message)
  │  ├─ step_progress(step_id, status)
  │  └─ finished(result)
  │
  └─ UI updates:
     ├─ Job list table
     ├─ Workflow graph visualization
     ├─ Console output
     └─ Event history

┌─────────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING                                │
└─────────────────────────────────────────────────────────────────┘

Error Scenarios:
  1. Component not found
     └─ Raise KeyError → Log error → Mark step as failed

  2. Step execution exception
     └─ Catch exception → Log error → Store in StepResult

  3. Dependency deadlock
     └─ Detect cycle → Raise ValueError → Fail pipeline

  4. Timeout
     └─ (Future: Add timeout per step)

  5. Resource exhaustion
     └─ (Future: Add resource limits)

```

## Component Types

### Step Types
- **FETCH**: Fetch data from source
- **PARSE**: Parse HTML/content
- **TRANSFORM**: Transform data
- **QC**: Quality control/validation
- **EXPORT**: Export to destination (runs sequentially)

### Component Categories
- **scraper**: Source-specific scrapers
- **engine**: HTTP/Selenium/Playwright engines
- **processor**: Data processors (QC, normalization, etc.)
- **exporter**: Export destinations (DB, file, API)

## State Transitions

```
Job States:
  PENDING → RUNNING → SUCCESS
                ↓
             FAILED
                ↓
            RETRY → RUNNING → ...

Step States:
  PENDING → READY → RUNNING → SUCCESS
                              ↓
                           FAILED
```

## Data Flow

```
Configuration (YAML)
  ↓
CompiledPipeline
  ↓
RunContext (runtime state)
  ├─ step_results: {step_id → StepResult}
  └─ metadata: {key → value}
  ↓
RunResult (final output)
  ├─ status: success/failed/partial
  ├─ step_results: all step results
  └─ item_count: number of items processed
```

