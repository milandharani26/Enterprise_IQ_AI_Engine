# Makefile for EnterpriseIQ AI (FastAPI + Next.js)

PYTHON ?= python3

# --- Docker & Database ---
up:
	docker compose --project-directory . -f infra/docker/docker-compose.yml up -d

down:
	docker compose --project-directory . -f infra/docker/docker-compose.yml down

logs:
	docker compose --project-directory . -f infra/docker/docker-compose.yml logs -f

ps:
	docker compose --project-directory . -f infra/docker/docker-compose.yml ps

clean:
	docker compose --project-directory . -f infra/docker/docker-compose.yml down -v

prune:
	docker container prune -f
	docker image prune -f

# --- Local Development ---
# Run both FastAPI and Next.js concurrently with hot-reloading
dev:
	$(PYTHON) -m poetry run python scripts/run_dev.py

# --- Production & Build ---
# Build Next.js to static files in cpanel/out
build-cpanel:
	cd cpanel && npm run build

# Run the unified server serving both API and static frontend
prod:
	$(PYTHON) -m poetry run python main.py

# Run Celery worker for async document indexing (requires Redis on localhost:6379).
dev-worker:
	PYTHONPATH=$(shell pwd) $(PYTHON) -m poetry run python -m celery -A engine.pipelines.tasks.celery_app worker --loglevel=info

# --- Utilities ---
# Install Next.js frontend dependencies
dev-cpanel-install:
	cd cpanel && npm install

# Run backend database migrations
migrate:
	$(PYTHON) -m poetry run python scripts/run_migrate.py

# Recreate DB with pgvector (wipes docker volume — dev only)
db-pgvector:
	docker compose --project-directory . -f infra/docker/docker-compose.yml down db
	-docker volume rm enterprise_iq_ai_engine_pgdata
	docker compose --project-directory . -f infra/docker/docker-compose.yml up -d db
	@echo "Waiting for Postgres..."
	@sleep 6
	$(PYTHON) -m poetry run python scripts/run_migrate.py
