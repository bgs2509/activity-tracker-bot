# Single-stage build for PoC Level 1
FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY services/tracker_activity_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/tracker_activity_bot/ ./

# Set PYTHONPATH to include app directory
ENV PYTHONPATH=/app:$PYTHONPATH

# Run application with new src/ structure
# For testing: keep container alive without starting the bot
CMD ["tail", "-f", "/dev/null"]
