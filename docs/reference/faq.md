# FAQ

**Where is the main documentation index?**
See `docs/misc/documentation_index.md` for a categorized map of all guides.

**Which orchestrator should I use?**
Use the legacy orchestrator for production and treat the pipeline-pack as experimental until browser engines are complete.

**Do I need database or browser dependencies installed?**
Only when using DB exporters or browser engines; keep HTTP-only deployments lean.

**How do I monitor runs?**
Use the dashboard in `frontend-dashboard/` and Airflow task logs for detailed traces.
