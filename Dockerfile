# Use the official Python 3.12 slim image to match project runtime requirements
FROM python:3.12-slim

ARG GIT_SHA=unknown
ARG GIT_BRANCH=unknown
ARG BUILD_TIMESTAMP=unknown
ARG REPO_URL=https://github.com/sgajbi/lotus-manage
ARG IMAGE_DIGEST=unknown
ARG CI_PIPELINE_ID=local
ARG APP_VERSION=0.1.0

LABEL org.opencontainers.image.title="lotus-manage" \
    org.opencontainers.image.description="Discretionary portfolio management execution and lifecycle service for Lotus platform." \
    org.opencontainers.image.version="${APP_VERSION}" \
    org.opencontainers.image.revision="${GIT_SHA}" \
    org.opencontainers.image.ref.name="${GIT_BRANCH}" \
    org.opencontainers.image.created="${BUILD_TIMESTAMP}" \
    org.opencontainers.image.source="${REPO_URL}" \
    org.opencontainers.image.url="${REPO_URL}" \
    org.opencontainers.image.vendor="Lotus" \
    lotus.ci.pipeline_id="${CI_PIPELINE_ID}" \
    lotus.image.digest="${IMAGE_DIGEST}"

# Set environment variables to prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LOTUS_IMAGE_GIT_SHA="${GIT_SHA}" \
    LOTUS_IMAGE_GIT_BRANCH="${GIT_BRANCH}" \
    LOTUS_IMAGE_BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
    LOTUS_IMAGE_REPO_URL="${REPO_URL}" \
    LOTUS_IMAGE_DIGEST="${IMAGE_DIGEST}" \
    LOTUS_IMAGE_CI_PIPELINE_ID="${CI_PIPELINE_ID}"

# Create a non-root user for security compliance
RUN adduser --disabled-password --gecos '' dpm-user

# Set the working directory
WORKDIR /app

# Copy package metadata, source, and operational scripts
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install runtime dependencies only
RUN pip install --upgrade pip && pip install .

# Change ownership of the application files to the non-root user
RUN chown -R dpm-user:dpm-user /app

# Switch to the non-root user
USER dpm-user

# Expose the port uvicorn will listen on
EXPOSE 8000

# Container-level readiness check using Python stdlib (no curl dependency)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"

# Command to run the application
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
