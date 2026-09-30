"""Aggregate router mounted at ``settings.api_prefix``."""

from fastapi import APIRouter

from app.api.routes import (
    agents,
    auth,
    candidates,
    dashboard,
    evaluation,
    events,
    health,
    integrations,
    knowledge,
    roles,
    skill_tests,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(roles.router)
api_router.include_router(candidates.router)
api_router.include_router(dashboard.router)
api_router.include_router(evaluation.router)
api_router.include_router(skill_tests.router)
api_router.include_router(events.router)
api_router.include_router(knowledge.router)
api_router.include_router(agents.router)
api_router.include_router(integrations.router)
