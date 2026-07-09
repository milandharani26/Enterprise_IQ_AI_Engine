# Stage 1: Build Next.js frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY cpanel/package.json cpanel/package-lock.json ./
RUN npm ci
COPY cpanel ./
ARG NEXT_PUBLIC_API_URL=/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# Stage 2: Create all-in-one runner image
FROM python:3.11-slim
WORKDIR /app

# Expose FastAPI port
EXPOSE 8000

# Install system dependencies (Postgres, Redis, Supervisor, Build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql \
    postgresql-contrib \
    postgresql-server-dev-all \
    redis-server \
    supervisor \
    git \
    make \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone and compile pgvector
RUN git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector

# Install Poetry
RUN pip install poetry

# Copy backend dependencies
COPY pyproject.toml poetry.lock ./

# Install python dependencies globally inside the container
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy static frontend export from Builder Stage
COPY --from=frontend-builder /build/out /app/cpanel/out

# Copy application code
COPY engine /app/engine
COPY shared /app/shared
COPY scripts /app/scripts
COPY main.py /app/main.py
COPY alembic.ini /app/alembic.ini

# Copy entrypoint and supervisord configuration
COPY infra/docker/entrypoint.sh /app/entrypoint.sh
COPY infra/docker/supervisord.conf /etc/supervisor/supervisord.conf

# Setup execution permissions for entrypoint
RUN chmod +x /app/entrypoint.sh

# Run entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
