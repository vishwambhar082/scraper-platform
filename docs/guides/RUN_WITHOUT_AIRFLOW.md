# Running Scraper Platform Without Airflow

Since you're experiencing issues with Airflow on Windows, you can run the scraper platform directly without Airflow. This approach uses the built-in pipeline runner.

## Prerequisites

Make sure you have Python 3.11+ installed and the virtual environment set up:

```bash
# Create virtual environment (if not already done)
python setup.py

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

## Running Scrapers Directly

### Using the Command Line

You can run any scraper directly using the command line:

```bash
# Run Alfabeta scraper in development mode
python -m src.entrypoints.run_pipeline --source alfabeta --environment dev

# Run with custom parameters
python -m src.entrypoints.run_pipeline --source alfabeta --environment dev --params '{"max_pages": 5}'

# Run in production mode
python -m src.entrypoints.run_pipeline --source alfabeta --environment prod
```

### Using the Desktop UI

The desktop UI provides a graphical way to run scrapers:

```bash
# Run the desktop UI
python run_ui.py
```

Then:
1. Navigate to the "Jobs" tab
2. Select your source (e.g., "alfabeta")
3. Choose environment (dev/prod)
4. Click "Run Pipeline"

### Running Specific Pipeline Steps

You can also run individual pipeline steps for testing:

```bash
# Run just the fetch step
python -m src.entrypoints.run_step --source alfabeta --step fetch --environment dev

# Run the parse step
python -m src.entrypoints.run_step --source alfabeta --step parse --environment dev
```

## Available Sources

The following sources are available:
- alfabeta
- argentina
- chile
- lafa
- quebec

## Environment Types

- `dev` - Development environment (uses test credentials and limited data)
- `prod` - Production environment (uses real credentials and full data sets)

## Configuration

Configuration files are located in the `config/` directory:
- `config/env/` - Environment-specific settings
- `config/sources/` - Source-specific settings

To set up your credentials:
1. Copy `.env.example` to `.env`
2. Edit `.env` with your actual credentials

## Monitoring and Logging

Logs are written to:
- Console output during execution
- `logs/` directory for persistent logs

You can increase verbosity by setting the log level:

```bash
# Set debug level logging
LOG_LEVEL=DEBUG python -m src.entrypoints.run_pipeline --source alfabeta --environment dev
```

## Benefits of Running Without Airflow

1. **No Windows compatibility issues** - Everything runs natively
2. **Faster startup** - No need to start multiple services
3. **Simpler debugging** - Direct console output
4. **Lower resource usage** - No database or scheduler overhead
5. **Easier development** - Quick iteration cycles

## Limitations Compared to Airflow

1. **No scheduling** - You need to trigger runs manually or with external schedulers
2. **No web UI for monitoring** - Except for the desktop UI
3. **No distributed execution** - Runs on a single machine
4. **No advanced workflow features** - Like retries, alerts, etc.

## When to Use Each Approach

### Use Direct Execution When:
- Developing or testing scrapers
- Running one-off scrapes
- Working in a development environment
- You don't need scheduling features

### Use Airflow When:
- You need scheduled execution
- You want web-based monitoring
- You're in a production environment
- You need advanced workflow features

## Troubleshooting

### ImportError Issues

If you get import errors, make sure you're running from the project root:

```bash
# Correct - run from project root
cd scraper-platform
python -m src.entrypoints.run_pipeline --source alfabeta --environment dev
```

### Missing Dependencies

If you get missing dependency errors:

```bash
# Install all dependencies
pip install -r requirements.txt
```

### Permission Errors

On Windows, you might need to run as administrator if you encounter permission errors with file access.

## Example Output

When running a scraper successfully, you should see output like:

```
[INFO] Starting pipeline run for alfabeta (dev)
[INFO] Running step: fetch_listings
[INFO] Fetching 25 product URLs
[INFO] Running step: parse_products
[INFO] Parsed 25 products
[INFO] Running step: export_database
[INFO] Exported 25 products to database
[INFO] Pipeline completed successfully in 12.3s
```