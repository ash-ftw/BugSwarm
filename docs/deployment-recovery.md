# Deployment Recovery

Use this when Docker Desktop images, containers, or volumes have been deleted or corrupted.

## Docker Compose Rebuild

From the repository root:

```powershell
.\scripts\recover-docker.ps1 -Pull
```

Useful options:

- `-NoCache` rebuilds all local images without Docker layer cache.
- `-ResetVolumes` deletes the compose database volume and starts with an empty PostgreSQL database.
- `-SkipStart` builds images but does not start the stack.

The recovery script recreates `.env` from `.env.example` when needed, ensures storage directories exist, runs `docker compose build`, and starts the stack with healthchecks.

Expected local URLs:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/api/health`
- BuggyShop demo target: `http://localhost:8090`

## When Images Were Deleted

Docker Compose can rebuild every app-owned image from source:

- `bugswarm-backend`
- `bugswarm-worker`
- `bugswarm-frontend`
- `bugswarm-buggyshop`

The base images are pulled again by Docker:

- `python:3.12-slim`
- `python:3.12-bookworm`
- `python:3.12-alpine`
- `node:22-alpine`
- `postgres:16-alpine`
- `redis:7-alpine`

If Docker Desktop was reset, make sure it is running before using the recovery script.

## Database Reset

Use `-ResetVolumes` only when you intentionally want to remove local PostgreSQL data:

```powershell
.\scripts\recover-docker.ps1 -ResetVolumes -Pull
```

The backend container runs Alembic migrations on startup by default. Set `RUN_MIGRATIONS=false` in `.env` only if migrations are being run separately.
