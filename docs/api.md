# BugSwarm API Notes

Base path: `/api`

## Auth

- `POST /auth/register` creates a user and returns a bearer token.
- `POST /auth/login` returns a bearer token.
- `GET /auth/me` returns the current user.

## Projects

- `GET /projects` lists owned projects.
- `POST /projects` creates a target project.
- `POST /projects/demo` creates or refreshes the BuggyShop demo project for the current user.
- `GET /projects/{project_id}` returns project details, scopes, and provider configs.
- `PATCH /projects/{project_id}` updates project settings.
- `DELETE /projects/{project_id}` deletes a project.

## Auth Profiles

- `GET /projects/{project_id}/auth-profiles` lists target-site login profiles.
- `POST /projects/{project_id}/auth-profiles` creates a form or storage-state auth profile.
- `PATCH /auth-profiles/{profile_id}` updates selectors, credentials, storage-state path, or active status.
- `DELETE /auth-profiles/{profile_id}` deletes a target auth profile.

Auth profile responses never include the stored password value. Passwords are encrypted at rest and decrypted only when a selected profile is queued into a worker job.

## Test Runs

- `POST /projects/{project_id}/test-runs` queues browser agents.
- `GET /projects/{project_id}/test-runs` lists project runs.
- `GET /test-runs/{test_run_id}` returns run progress, agents, coverage, and counts.
- `POST /test-runs/{test_run_id}/stop` cancels a queued or running test run.
- `GET /test-runs/{test_run_id}/test-cases` returns generated tests and reasoning sessions.
- `GET /test-runs/{test_run_id}/report?format=json|markdown` exports a run report.
- `WS /ws/test-runs/{test_run_id}` streams run, agent, AI, bug, and replay events.

## Bugs And Replay

- `GET /projects/{project_id}/bugs` lists project bugs.
- `GET /bugs/{bug_id}` returns bug evidence.
- `PATCH /bugs/{bug_id}` updates triage status.
- `GET /bugs/{bug_id}/validation` returns LLM council validation sessions and provider votes.
- `POST /bugs/{bug_id}/validate` queues LLM council validation and severity classification.
- `GET /bugs/{bug_id}/artifacts/{artifact_id}` downloads an evidence artifact.
- `GET /bugs/{bug_id}/replay` returns replay steps and attempts.
- `POST /bugs/{bug_id}/replay` queues a replay worker task.
- `GET /bugs/{bug_id}/playwright-script` generates a standalone Playwright script.

## System

- `GET /system/config` returns environment and AI provider status.
- `GET /system/queue` returns Redis/Celery queue depth, broker connectivity, and the recommended worker replica count.
- `GET /system/queue/metrics` returns Prometheus text metrics for pending Celery tasks, queue-depth targets, replica limits, and Redis connectivity.
- `GET /system/retention` returns current retention policy.
- `POST /system/retention/cleanup` queues a retention cleanup task. Pass `{ "dry_run": true }` to count expired records/files without deleting them.
