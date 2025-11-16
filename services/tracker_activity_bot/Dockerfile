# Single-stage build for PoC Level 1
FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY services/tracker_activity_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/tracker_activity_bot/ ./

# Security: Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Set PYTHONPATH to include app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Security: Switch to non-root user
USER appuser

# Run application with new src/ structure
CMD ["python", "-m", "src.main"]

# For testing: keep container alive without starting the bot
# CMD ["tail", "-f", "/dev/null"]
