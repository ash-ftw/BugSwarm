# BugSwarm

BugSwarm is an AI-powered web testing swarm. It uses browser agents to explore a target web app, collect evidence, detect bugs, and prepare replayable reports. This repository is scaffolded from `BugSwarm_Complete_Documentation.md`.

## Current Status

Phase 1 through Phase 12 are in place:

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
- Phase 4 run hardening: queued/running/reporting/completed agent lifecycle events, per-run progress summaries, duration/action-limit handling, stop broadcasts, and stale worker reconciliation.
- Phase 5 AI generation: page-context evidence packets, Groq/GPT-OSS/Gemini/OpenRouter provider orchestration, persisted reasoning sessions and provider votes, generated test cases and steps, safe execution of accepted/seeded tests, and dashboard panels for AI tests and council results.
- Phase 6 bug detection and reporting: rule-based HTTP, console, network, blank-page, crash, loading, and interaction bug creation with fingerprints, artifacts, replay steps, bug APIs, artifact access, JSON/Markdown reports, and dashboard triage views.
- Phase 7 replay system: replay worker task execution, per-step replay screenshots, replay attempt history stored as reports, Playwright script generation, replay APIs, and dashboard controls for replaying and copying scripts.
- Phase 8 demo readiness: BuggyShop intentional-bug target app, one-click demo project creation, retention policy and cleanup APIs, dashboard retention controls, sample reports, architecture/API docs, and backend/worker smoke tests.
- Phase 9 deployment recovery: rebuild scripts for wiped Docker Desktop state, Minikube manifests and build script, container healthchecks, backend migration entrypoint, worker concurrency/autoscale controls, and CI workflow checks.
- Phase 10 target authentication: project auth profile CRUD, encrypted stored target passwords, BuggyShop demo login profile, test-run auth profile selection, worker form login/storage-state handling, and live auth events.
- Phase 11 bug validation council: LLM provider review of bug evidence, consensus validity votes, AI severity classification, suggested fixes, persisted validation sessions, validation APIs, and dashboard validation controls.
- Phase 12 queue-depth autoscaling signals: Redis/Celery queue-depth APIs, Prometheus metrics, dashboard autoscale status, Kubernetes scrape annotations, and optional KEDA Redis ScaledObject manifests for production worker scaling.

## Local Setup

1. Copy `.env.example` to `.env` and update secrets when needed.
2. Start infrastructure and apps:

```bash
docker compose up --build
```

If Docker Desktop images or containers were deleted, rebuild from a clean state:

```powershell
.\scripts\recover-docker.ps1 -Pull
```

3. Open:

- Backend API health: `http://localhost:8000/api/health`
- Frontend dashboard: `http://localhost:5173`
- BuggyShop demo target: `http://localhost:8090`

4. For a deterministic demo, register a user, open Projects, click Demo target, and start a run.

For Minikube recovery after deleting the cluster or its images:

```powershell
.\scripts\minikube-deploy.ps1 -Start
```

See `docs/deployment-recovery.md` and `docs/minikube.md` for the full recovery workflow.

## Project Layout

```text
backend/   FastAPI API, SQLAlchemy models, Alembic migrations
frontend/  React TypeScript dashboard
worker/    Browser-agent, LLM council, detection, and reporting worker
demo/      BuggyShop intentional-bug target app
docs/      Architecture and API reference notes
k8s/       Minikube Kubernetes manifests
scripts/   Docker and Minikube recovery scripts
sample-reports/  Demo report examples
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

1. Add GitHub/Jira issue export integrations.
2. Expand final presentation materials and screenshots.

## Verification

Useful local checks:

```bash
python -m compileall backend/app worker/bugswarm_worker demo/buggyshop
python -m unittest discover backend/tests
python -m unittest discover worker/tests
cd frontend && npm run build
cd frontend && npm run lint
docker compose config --no-interpolate
```
