# Next.js + FastAPI AI Project Setup Guide

This document serves as both the **scaffolding plan** to initialize the new project and the **ultimate documentation** for the resulting architecture. 

It replicates the proven structure of your current Python/Poetry backend while swapping the frontend to a modern **Next.js** implementation.

---

## 1. Architecture Overview

The application is split into two primary pieces governed by a single monolithic repository:

- **Backend (`engine/`)**: A Python-based **FastAPI** application managing all core API routes, database connections (SQLAlchemy), and domain logic. Managed via **Poetry**.
- **Frontend (`cpanel/`)**: A **Next.js** (App Router) application built with React, TypeScript, and Tailwind CSS. Managed via **npm**.

> [!IMPORTANT]
> The backend acts as a path dependency in Poetry. This means you run `poetry install` at the **root** of the project, not inside the `engine` directory.


## 2. Step-by-Step Scaffolding Commands

To build this project from scratch, open your terminal and run the following steps in order.

### Phase 1: Initialize the Root Environment
```bash
# 1. Create your new project folder and navigate into it
mkdir my-new-ai-project
cd my-new-ai-project

# 2. Initialize Poetry (follow the interactive prompts or accept defaults)
poetry init

# 3. Configure Poetry to create the virtual environment inside the project (.venv)
poetry config virtualenvs.in-project true

# 4. Add the core backend dependencies (this will now create a .venv folder here)
poetry add fastapi uvicorn sqlalchemy asyncpg alembic
```

### Phase 2: Scaffold the Next.js Frontend (`cpanel/`)
```bash
# 4. Generate the Next.js frontend using the exact required configuration
npx create-next-app@latest cpanel \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --use-npm
```

### Phase 3: Scaffold the FastAPI Backend (`engine/`)
```bash
# 5. Create the required backend directories
mkdir engine
mkdir engine/core
mkdir engine/domains
mkdir engine/models
mkdir engine/routes
mkdir engine/services

# 6. Create backend foundation files
touch engine/__init__.py
touch engine/.env.example
touch main.py
```

### Phase 4: Scaffold the Supporting Directories
```bash
# 7. Create folders for shared code, infrastructure, testing, and scripts
mkdir shared shared/utils
mkdir scripts
mkdir infra infra/docker
mkdir docs
mkdir tests
```

---

## 3. The Resulting Folder Structure

Once you have run the scaffolding commands above, your project will look exactly like this:

```text
project-root/
├── main.py                 # Main entry point for the FastAPI server
├── pyproject.toml          # Poetry configuration and backend dependencies
├── poetry.lock             # Poetry lockfile
├── README.md               # Your project's main readme
│
├── engine/                 # 🐍 FastAPI Backend Logic
│   ├── .env.example        # Example environment variables (copy to .env)
│   ├── __init__.py
│   ├── core/               # App configuration, security, auth, and lifecycle
│   ├── domains/            # Business logic and domain-specific modules (e.g. integrations)
│   ├── models/             # Database models (SQLAlchemy)
│   ├── routes/             # FastAPI routers and endpoints
│   ├── services/           # Service layer and external API calls
│   └── alembic/            # Database migrations
│
├── cpanel/                 # ⚛️ Next.js Frontend (Control Panel)
│   ├── package.json        # Frontend dependencies and scripts
│   ├── next.config.mjs     # Next.js configuration
│   ├── tailwind.config.ts  # Tailwind CSS configuration
│   └── src/
│       ├── app/            # Next.js App Router (Pages, Layouts, API routes)
│       ├── components/     # Reusable React components (e.g., shadcn-ui)
│       ├── lib/            # Utility functions and shared frontend logic
│       └── styles/         # Global CSS and Tailwind directives
│
├── shared/                 # 📦 Shared Backend Utilities
│   └── utils/              # Helper functions (e.g., environment managers)
│
├── scripts/                # 🛠️ Cross-platform Helper Scripts
│   ├── run_dev.py          # Script to start development servers easily
│   └── run_migrate.py      # Script to apply DB migrations
│
├── infra/                  # 🐳 Infrastructure Configuration
│   └── docker/
│       ├── docker-compose.yml
│       └── Dockerfile
│
├── docs/                   # 📚 Additional Documentation
│   └── setup_guide.md
│
└── tests/                  # 🧪 Automated Tests
    ├── conftest.py         # Pytest configuration and fixtures
    └── main_test.py        # Example test files
```

> [!TIP]
> Keep `engine/` strictly for Python backend logic and `cpanel/` strictly for frontend logic. Shared Python constants should go into the `shared/` directory.

---

## 4. Quick Start & Execution Guide

After the project is scaffolded, here is how you and your team will run the project daily.

### Backend Development

1. **Install Dependencies:**
   Make sure you are at the project root and run:
   ```bash
   poetry install
   ```
2. **Setup Environment Variables:**
   ```bash
   cp engine/.env.example engine/.env
   # Edit engine/.env with your DATABASE_URL
   ```
3. **Start the API Server:**
   Run the entrypoint directly using Poetry.
   ```bash
   poetry run python main.py
   # Alternatively: poetry run uvicorn main:app --reload
   ```
   *The API will be available at `http://localhost:8000`. Swagger docs at `/docs`.*

### Frontend Development

1. **Install Dependencies:**
   ```bash
   cd cpanel
   npm install
   ```
2. **Start the Next.js Server:**
   ```bash
   npm run dev
   ```
   *The Control Panel will be available at `http://localhost:3000`.*

---

## 5. Deployment & Docker (Optional)

For production or containerized development, utilize the `infra/docker/` setup:

```bash
cd infra/docker
docker-compose up -d --build
```
This will spin up both the FastAPI backend and the Next.js frontend in isolated containers alongside your Postgres/Redis databases.
