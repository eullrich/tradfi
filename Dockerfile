FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml requirements.txt* ./
RUN pip install --no-cache-dir -e . || pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Start command - use shell form to expand $PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
