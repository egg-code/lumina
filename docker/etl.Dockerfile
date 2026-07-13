# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /workspace

# Copy the workspace
COPY . .

# Sync only the ETL package
WORKDIR /workspace/etl
RUN uv sync --frozen --no-dev

# Run the ETL orchestrator
CMD ["uv", "run", "python", "main.py"]
