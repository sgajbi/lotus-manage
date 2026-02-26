# Use the official Python 3.11 slim image for a smaller footprint
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Create a non-root user for security compliance
RUN adduser --disabled-password --gecos '' dpm-user

# Set the working directory
WORKDIR /app

# Copy only runtime requirements first to leverage Docker layer caching
COPY requirements-prod.txt .

# Install runtime dependencies only
RUN pip install -r requirements-prod.txt

# Copy the core application code
COPY src/ ./src/

# Change ownership of the application files to the non-root user
RUN chown -R dpm-user:dpm-user /app

# Switch to the non-root user
USER dpm-user

# Expose the port uvicorn will listen on
EXPOSE 8000

# Container-level healthcheck using Python stdlib (no curl dependency)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/docs', timeout=3)"

# Command to run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
