FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY data/ data/

# Install the package
RUN pip install --no-cache-dir .

# Create directory for persistent data
RUN mkdir -p /data

# Set environment variables
ENV TRADFI_DB_PATH=/data/cache.db
ENV TRADFI_CONFIG_PATH=/data/config.json
ENV TRADFI_REFRESH_UNIVERSES=dow30,nasdaq100,sp500

# Expose port
EXPOSE 8000

# Start the API server
CMD ["uvicorn", "tradfi.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
