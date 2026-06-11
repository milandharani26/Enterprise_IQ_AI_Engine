# Makefile for EnterpriseIQ AI (FastAPI + Next.js)

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
	python -m poetry run python scripts/run_dev.py

# --- Production & Build ---
# Build Next.js to static files in cpanel/out
build-cpanel:
	cd cpanel && npm run build

# Run the unified server serving both API and static frontend
prod:
	python -m poetry run python main.py

# --- Utilities ---
# Install Next.js frontend dependencies
dev-cpanel-install:
	cd cpanel && npm install

# Run backend database migrations
migrate:
	python -m poetry run python scripts/run_migrate.py
