# Migration Checklist

Step-by-step checklist for migrating to structured logging.

## Phase 1: Installation & Verification (Day 1)

### 1.1 Install Dependencies
- [ ] Run `pip install -r requirements.txt`
- [ ] Verify structlog is installed: `python -c "import structlog; print(structlog.__version__)"`
- [ ] Should see version >= 23.1.0

### 1.2 Run Tests
- [ ] Run tests: `pytest src/app_logging/test_structured_logging.py -v`
- [ ] Verify all 9 tests pass
- [ ] Check for any import errors or dependency issues

### 1.3 Run Examples
- [ ] Run examples: `python -m src.app_logging.examples`
- [ ] Check `logs/examples/` directory was created
- [ ] Verify JSONL files contain valid JSON
- [ ] Use `jq` to inspect: `cat logs/examples/example_scraper.jsonl | jq`

### 1.4 Read Documentation
- [ ] Read [QUICK_START.md](QUICK_START.md)
- [ ] Skim [STRUCTURED_LOGGING_GUIDE.md](STRUCTURED_LOGGING_GUIDE.md)
- [ ] Review [examples.py](examples.py) for code patterns

## Phase 2: Basic Integration (Week 1)

### 2.1 Configure Logging in Application Startup
- [ ] Find application entry point (e.g., `src/entrypoints/run_pipeline.py`)
- [ ] Add structured logging configuration:
  ```python
  from src.app_logging import configure_structured_logging

  configure_structured_logging(
      log_level="INFO",
      enable_console=True,
      enable_file=True,
  )
  ```
- [ ] Test application starts without errors
- [ ] Verify log files are created in `logs/`

### 2.2 Update One Module as Proof of Concept
- [ ] Choose a small, non-critical module to migrate first
- [ ] Replace imports:
  ```python
  # Before
  import logging
  logger = logging.getLogger(__name__)

  # After
  from src.app_logging import get_structured_logger
  log = get_structured_logger(__name__)
  ```
- [ ] Update log statements:
  ```python
  # Before
  logger.info(f"Processed {count} items")

  # After
  log.info("items_processed", count=count)
  ```
- [ ] Test the module
- [ ] Verify logs appear in `logs/scraper_structured.jsonl`
- [ ] Inspect logs with `jq` to verify format

### 2.3 Add Context to One Scraper
- [ ] Choose one scraper to add context
- [ ] Add RunContext:
  ```python
  from src.app_logging import RunContext

  with RunContext(run_id=run_id, source=source):
      # Scraping logic
  ```
- [ ] Run the scraper
- [ ] Verify context appears in all log entries
- [ ] Check that context is automatically included

## Phase 3: Expand Usage (Week 2-3)

### 3.1 Migrate Core Modules
- [ ] Identify core modules (scrapers, pipelines, processors)
- [ ] Create list of modules to migrate
- [ ] Migrate one module per day
- [ ] Test each module after migration
- [ ] Keep checklist of completed modules

#### Migration Template for Each Module:
- [ ] Update imports
- [ ] Replace all log statements
- [ ] Add appropriate context (RunContext, StepContext, etc.)
- [ ] Test module functionality
- [ ] Review generated logs
- [ ] Update any tests that check log output

### 3.2 Add Context to Pipelines
- [ ] Identify pipeline execution points
- [ ] Add StepContext to each step:
  ```python
  from src.app_logging import StepContext

  with StepContext(step_id="fetch", step_type="FETCH", step_index=0):
      # Step logic
  ```
- [ ] Test pipeline execution
- [ ] Verify step context in logs

### 3.3 Update Error Handling
- [ ] Find all try/except blocks
- [ ] Replace error logging with `log.exception()`:
  ```python
  try:
      risky_operation()
  except Exception:
      log.exception("operation_failed", operation="risky_operation")
  ```
- [ ] Test error scenarios
- [ ] Verify tracebacks in logs

## Phase 4: Optimization (Week 4)

### 4.1 Configure for Production
- [ ] Update production configuration:
  ```python
  from src.app_logging import setup_production_logging

  if os.getenv("ENVIRONMENT") == "production":
      setup_production_logging(
          log_level="INFO",
          enable_console=False,
      )
  ```
- [ ] Test in staging environment
- [ ] Verify performance is acceptable
- [ ] Adjust log level if needed

### 4.2 Configure File Rotation
- [ ] Set appropriate rotation settings:
  ```python
  configure_structured_logging(
      max_bytes=100 * 1024 * 1024,  # 100 MB
      backup_count=10,
  )
  ```
- [ ] Test rotation by generating large log volume
- [ ] Verify old logs are backed up
- [ ] Set up log cleanup/archival process

### 4.3 Add Monitoring
- [ ] Choose observability tool (Elasticsearch, Loki, etc.)
- [ ] Configure log shipping (Filebeat, Promtail, etc.)
- [ ] Set up log ingestion pipeline
- [ ] Create dashboards for key metrics
- [ ] Set up alerts for errors/warnings

## Phase 5: Full Migration (Week 5-6)

### 5.1 Complete Module Migration
- [ ] Migrate remaining modules
- [ ] Update all log statements to structured format
- [ ] Remove old logging configurations
- [ ] Update all imports

### 5.2 Update Tests
- [ ] Find tests that check log output
- [ ] Update to expect JSON format
- [ ] Update any log assertions
- [ ] Ensure tests pass

### 5.3 Update Documentation
- [ ] Update developer documentation
- [ ] Add logging examples to README
- [ ] Document logging conventions
- [ ] Update onboarding docs

## Phase 6: Cleanup & Validation (Week 7)

### 6.1 Code Cleanup
- [ ] Search for old logging patterns:
  ```bash
  grep -r "logging.getLogger" src/
  grep -r "from src.common.logging_utils import get_logger" src/
  ```
- [ ] Remove unused imports
- [ ] Clean up old logging configurations
- [ ] Remove deprecated code

### 6.2 Verify Sensitive Data Masking
- [ ] Generate logs with test sensitive data
- [ ] Verify passwords are masked
- [ ] Verify API keys are masked
- [ ] Verify tokens are masked
- [ ] Verify URLs with credentials are masked
- [ ] Add custom sensitive fields if needed

### 6.3 Performance Testing
- [ ] Run performance tests
- [ ] Measure logging overhead
- [ ] Compare with baseline
- [ ] Optimize if needed (disable caller info, reduce log level, etc.)

### 6.4 Integration Testing
- [ ] Test full scraping pipeline
- [ ] Test error scenarios
- [ ] Test high-volume logging
- [ ] Test concurrent execution
- [ ] Verify logs are complete and accurate

## Phase 7: Production Deployment (Week 8)

### 7.1 Pre-Deployment Checklist
- [ ] All modules migrated
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Monitoring configured
- [ ] Rollback plan ready

### 7.2 Staging Deployment
- [ ] Deploy to staging
- [ ] Run full test suite
- [ ] Monitor logs for issues
- [ ] Verify log shipping works
- [ ] Check dashboards
- [ ] Fix any issues found

### 7.3 Production Deployment
- [ ] Deploy to production (canary or rolling deployment)
- [ ] Monitor closely for first few hours
- [ ] Check log volume
- [ ] Verify no errors
- [ ] Check performance metrics
- [ ] Verify monitoring/alerting works

### 7.4 Post-Deployment
- [ ] Monitor for 24-48 hours
- [ ] Review logs for any issues
- [ ] Check disk usage
- [ ] Verify rotation works
- [ ] Collect feedback from team
- [ ] Document any issues/learnings

## Common Issues Checklist

### Troubleshooting Checklist
If logs aren't appearing:
- [ ] Check log level configuration
- [ ] Verify file permissions
- [ ] Check disk space
- [ ] Verify logger name is correct
- [ ] Check that logging is configured before first log

If context isn't appearing:
- [ ] Verify context is bound in same thread
- [ ] Check context scope (inside context manager?)
- [ ] Use `get_context()` to debug
- [ ] Verify `inject_context()` processor is enabled

If performance is poor:
- [ ] Disable caller info: `enable_caller_info=False`
- [ ] Reduce log level to INFO or WARNING
- [ ] Disable console output in production
- [ ] Enable logger caching: `cache_logger_on_first_use=True`

If sensitive data isn't masked:
- [ ] Check field names match SENSITIVE_FIELD_NAMES
- [ ] Add custom patterns if needed
- [ ] Verify `mask_sensitive_data()` processor is enabled
- [ ] Test with known sensitive data patterns

## Success Criteria

### Migration is Complete When:
- [ ] All modules use structured logging
- [ ] All log statements are structured (no string formatting)
- [ ] Context is used appropriately (Run, Step, Task)
- [ ] Sensitive data is properly masked
- [ ] Logs are shipped to monitoring system
- [ ] Dashboards and alerts are configured
- [ ] Documentation is updated
- [ ] Team is trained on new system
- [ ] Performance is acceptable
- [ ] No critical issues in production

### Quality Indicators:
- [ ] Logs are machine-readable (valid JSON)
- [ ] Context is consistent across related logs
- [ ] Log volume is reasonable (not too verbose)
- [ ] Important events are logged at appropriate levels
- [ ] Errors include sufficient context for debugging
- [ ] No sensitive data leaks in logs
- [ ] Log rotation prevents disk issues
- [ ] Team can easily search/analyze logs

## Post-Migration

### Ongoing Maintenance
- [ ] Periodically review log patterns
- [ ] Update sensitive data patterns as needed
- [ ] Adjust log levels based on needs
- [ ] Monitor log volume trends
- [ ] Update dashboards as needed
- [ ] Train new team members
- [ ] Keep documentation current

### Future Enhancements
- [ ] Add distributed tracing integration
- [ ] Implement log sampling for high-volume scenarios
- [ ] Add custom processors for specific needs
- [ ] Integrate with APM tools
- [ ] Add automated log analysis
- [ ] Implement log-based metrics

## Resources

- [QUICK_START.md](QUICK_START.md) - Quick reference
- [STRUCTURED_LOGGING_GUIDE.md](STRUCTURED_LOGGING_GUIDE.md) - Complete guide
- [examples.py](examples.py) - Code examples
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [README.md](README.md) - Module overview

## Team Communication

### Announce to Team:
- [ ] Send migration plan to team
- [ ] Schedule training session
- [ ] Share documentation links
- [ ] Set up Slack/Teams channel for questions
- [ ] Establish migration timeline
- [ ] Assign responsibilities

### Training Topics:
- [ ] How to use structured logging
- [ ] How to add context
- [ ] How to read JSON logs
- [ ] How to use monitoring dashboards
- [ ] Best practices
- [ ] Troubleshooting common issues

## Notes

Use this space to track migration-specific notes, decisions, and issues:

---

**Migration Start Date:** ________________

**Migration Completion Target:** ________________

**Migration Lead:** ________________

**Team Members Involved:** ________________

**Blockers/Issues:**
-
-
-

**Decisions Made:**
-
-
-

**Lessons Learned:**
-
-
-
