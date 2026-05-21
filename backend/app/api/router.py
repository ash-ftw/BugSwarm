from fastapi import APIRouter

from app.api.routes import auth, auth_profiles, bugs, health, projects, system, test_cases, test_runs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(auth_profiles.router, tags=["auth-profiles"])
api_router.include_router(test_runs.router, tags=["test-runs"])
api_router.include_router(test_cases.router, tags=["test-cases"])
api_router.include_router(bugs.router, tags=["bugs"])
