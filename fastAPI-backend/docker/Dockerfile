# Multi-stage build for Python 3.14 FastAPI application
FROM python:3.14-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --upgrade pip pipenv

# Copy Pipfile and install dependencies
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

# Production stage
FROM python:3.14-slim as production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

WORKDIR $APP_HOME

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from base
COPY --from=base /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy application code
COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appgroup $APP_HOME

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]