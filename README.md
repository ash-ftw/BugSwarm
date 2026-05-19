# BugSwarm

BugSwarm is an AI-powered web testing swarm. It uses browser agents to explore a target web app, collect evidence, detect bugs, and prepare replayable reports. This repository is scaffolded from `BugSwarm_Complete_Documentation.md`.

## Current Status

Phase 1 through the first Phase 4 slice are in place:

- FastAPI backend skeleton with health and provider-status APIs.
- SQLAlchemy model layer aligned with the documented PostgreSQL schema.
- Alembic migration setup.
- React + TypeScript dashboard shell using Vite.
- Worker package skeleton for scope checks, rule-based detection, LLM provider contracts, and deterministic council consensus.
- Docker Compose stack for PostgreSQL, Redis, backend, worker, and frontend.
- JWT registration/login APIs with PBKDF2 password hashing.
- Owner-scoped project CRUD APIs with allowed/excluded scope rules.
- Default Groq, GPT-OSS, and Gemini provider config records for each project.
- Login, register, projects, create-project, project detail, and project settings screens.
- Test-run creation, listing, detail, and stop APIs.
- Redis/Celery-backed worker dispatch for browser agents.
- Playwright explorer worker that crawls in-scope pages, captures screenshots, records agent steps, and persists discovered pages, page elements, console warnings/errors, and network failures.
- Test-run launch and live polling monitor screens in the dashboard.
- Redis pub/sub WebSocket stream for live test-run events at `/ws/test-runs/{test_run_id}`.
- Parallel Celery worker configuration and browser-agent strategies for explorer, form, navigation, and chaos agents.
- Live event feed and visited URL coverage panel in the test-run monitor.

## Local Setup

1. Copy `.env.example` to `.env` and update secrets when needed.
2. Start infrastructure and apps:

```bash
docker compose up --build
```

3. Open:

- Backend API health: `http://localhost:8000/api/health`
- Frontend dashboard: `http://localhost:5173`

## Project Layout

```text
backend/   FastAPI API, SQLAlchemy models, Alembic migrations
frontend/  React TypeScript dashboard
worker/    Browser-agent, LLM council, detection, and reporting worker
storage/   Runtime screenshots, traces, and reports
```

## AI Provider Defaults

The MVP keeps paid usage disabled unless configured by the user. Provider model IDs are environment-driven:

- `GROQ_API_KEY`, `GROQ_MODEL`
- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`
- `GPTOSS_BASE_URL`, `GPTOSS_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `AI_FREE_MODE`

Missing hosted API keys disable only that provider. A local GPT-OSS endpoint can be used without hosted API usage.

## Next Milestones

1. Add auth/profile forms for target-site login flows.
2. Add AI test generation and LLM council bug validation.
3. Generate bug reports, replay steps, and Playwright exports.
4. Add retention policies for screenshots, traces, and reports.
5. Harden worker autoscaling, retries, and cross-agent coordination.
