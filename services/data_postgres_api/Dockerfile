# Single-stage build for PoC Level 1
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/data_postgres_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/data_postgres_api/ ./

# Security: Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set PYTHONPATH to include app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8000

# Security: Switch to non-root user
USER appuser

# Run application with new src/ structure
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
