# Error Codes

| Code | Description | Resolution |
| --- | --- | --- |
| ERR-NODEP | Optional dependency missing (e.g., `psycopg2` or `selenium`). | Install the package only for environments that require DB exports or browser engines. |
| ERR-CONFIG | Pipeline configuration missing or using wrong key (`agent` vs `name`). | Align YAML with orchestrator expectations and reload DAGs. |
| ERR-ENGINE | Browser engine invoked but not implemented. | Switch to HTTP engine or complete the browser implementation before use. |
| ERR-DB | Database export failed due to credentials or schema issues. | Validate connection info and confirm tables exist per DB documentation. |
