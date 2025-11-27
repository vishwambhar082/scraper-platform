FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY requirements.txt /app/requirements.txt
COPY scraper-deps/ /app/scraper-deps/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
