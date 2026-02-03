#syntax=docker/dockerfile:1

# === Build stage: Install dependencies ===
FROM dhi.io/python:3.14-alpine3.23-dev AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies for building
RUN apk add --no-cache \
    build-base \
    libpq-dev \
    curl

# Install pipenv
RUN pip install --upgrade pip pipenv

# Copy Pipfile and install dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

# === Final Production stage: Create minimal runtime image ===
FROM dhi.io/python:3.14-alpine3.23-dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Install only runtime dependencies
RUN apk add --no-cache libpq

# Copy Python packages from builder
COPY --from=builder /opt/python/lib/python3.14/site-packages /opt/python/lib/python3.14/site-packages

# Copy application code
COPY ./app ./app

# Ensure proper permissions for non-root user (runs as gid 1000, uid 1000 by default in DHI)
RUN chown -R 1000:1000 $APP_HOME

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
