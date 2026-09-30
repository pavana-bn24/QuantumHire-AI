"""Health and readiness endpoints."""

from fastapi import APIRouter

from app.core.config import settings
from app.db.mongo import ping_database
from app.models import DatabaseHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health() -> HealthResponse:
    """Return ``{\"status\": \"ok\"}`` when the API process is serving traffic."""
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=DatabaseHealthResponse, summary="MongoDB check")
def database_health() -> DatabaseHealthResponse:
    """Report whether MongoDB is reachable (does not affect ``/health``)."""
    connected = ping_database()
    return DatabaseHealthResponse(
        status="ok" if connected else "degraded",
        database=settings.mongodb_db_name,
        connected=connected,
    )
