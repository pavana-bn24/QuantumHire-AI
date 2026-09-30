"""Dashboard aggregation endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import require_database, require_recruiter
from app.models import DashboardSummary
from app.services.metrics import build_dashboard_summary

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_database)]
)


@router.get("/summary", response_model=DashboardSummary, summary="Dashboard metrics")
def dashboard_summary(user: dict = Depends(require_recruiter)) -> dict:
    """Return candidate totals, stage counters and the pipeline breakdown."""
    return build_dashboard_summary()
