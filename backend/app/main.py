"""FastAPI application entrypoint for QuantumHire AI.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.mongo import close_mongo_connection, connect_to_mongo
from app.db.seed import run_seed

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
# PyMongo's DEBUG logging is extremely chatty - keep app logs verbose, driver terse.
logging.getLogger("pymongo").setLevel(logging.WARNING)
logger = logging.getLogger("quantumhire")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Connect to MongoDB and seed reference data on startup."""
    connect_to_mongo()

    if settings.seed_on_startup:
        run_seed()

    logger.info("%s ready in '%s' mode", settings.app_name, settings.environment)
    yield
    close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Recruiter workflow API for resume ingestion, recruiter-reviewed profiles, "
        "evidence-based candidate evaluations, editable skill tests, human approvals, "
        "workflow events, and webhook delivery."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", tags=["meta"], summary="Service banner")
def root() -> dict:
    """Small banner that points at the useful endpoints."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "health": f"{settings.api_prefix}/health",
        "docs": "/docs",
    }
