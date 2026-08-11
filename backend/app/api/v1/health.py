import logging

import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness check — process is up. Does not touch dependencies."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    """Readiness check — verifies DB and Redis are reachable."""
    settings = get_settings()
    checks = {"database": False, "redis": False}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.exception("Database readiness check failed")

    try:
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        checks["redis"] = True
    except Exception:
        logger.exception("Redis readiness check failed")

    status = "ok" if all(checks.values()) else "degraded"
    return {"status": status, "checks": checks}
