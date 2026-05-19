from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.routes.ws import router as websocket_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="BugSwarm API",
        version="0.1.0",
        description="Backend API for the BugSwarm AI-powered testing swarm.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)

    return app


app = create_app()
