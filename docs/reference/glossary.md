# Glossary

- **Agent**: A unit of work (fetch, parse, normalize, export) invoked by an orchestrator.
- **Pipeline**: Ordered set of agents defined in YAML for a specific source.
- **Pipeline pack**: Experimental agent framework in `src/pipeline_pack/` with registry-driven construction.
- **Orchestrator**: Controller that loads configs, builds agents, and shares context across steps.
- **Dashboard**: React + Vite UI (`frontend-dashboard/`) providing run visibility.
