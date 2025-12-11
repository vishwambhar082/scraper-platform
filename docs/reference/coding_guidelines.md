# Coding Guidelines

- Use type hints across new Python modules and prefer small, testable functions.
- Isolate optional dependencies so HTTP-only deployments succeed without extra packages.
- Run linters and relevant tests before merging; update configs and DAGs when introducing new agents or processors.
- Document non-obvious behavior and refresh status documents during release preparation.
