# Multi-stage Dockerfile for Cloud Run

# Build stage: install dependencies
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy lock/metadata for better layer caching
COPY pyproject.toml requirements.txt ./

# Install only runtime dependencies
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt


# Final stage: copy deps + app only
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed site-packages and scripts from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Download NLTK data required by langroid
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Copy application code
COPY agent_data/ /app/agent_data/

EXPOSE 8080

# Use Cloud Run provided $PORT or default to 8080
CMD ["bash", "-lc", "uvicorn agent_data.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
