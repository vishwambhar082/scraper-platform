# Developer Setup

Follow these exact steps to get a clean local environment.

## Prerequisites
- Python 3.11+
- Docker (optional for Airflow)

## Steps
```bash
# from repo root
python -m venv .venv
source .venv/bin/activate        # on Windows: .\.venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# create runtime folders
bash scripts/setup_dev.sh        # on Windows (Git Bash) this also works

# set env vars (example)
export AIRFLOW__CORE__FERNET_KEY=CHANGE_ME
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow

# run a pipeline
python -m src.entrypoints.run_pipeline --source alfabeta --environment dev

# launch UI
python run_ui.py

# run tests
pytest -q
```

## Tips
- Prefer `python -m ...` to ensure imports resolve consistently.
- Keep `.env` in sync with `config/env/example.env`.
- Use `pre-commit install` to enable lint/format on commit.

