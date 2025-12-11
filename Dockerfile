# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY scraper-deps/requirements.txt ./scraper-deps/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p sessions/cookies sessions/logs output/alfabeta/daily input

# Expose port for Airflow webserver
EXPOSE 8080

# Default command
CMD ["python", "run_ui.py"]