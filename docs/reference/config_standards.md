# Config Standards

- Keep defaults in `config/agents/defaults.yaml` or `config/pipeline_pack/defaults.yaml`; override per-source settings in pipeline files.
- Use descriptive step names in pipelines to improve logging clarity.
- Document proxy and credential requirements alongside source configurations.
- When adding new agents, register them in the appropriate registry and update YAML examples.
