import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.analyses import router as analyses_router
from app.api.v1.auth import router as auth_router
from app.api.v1.collection import router as collection_router
from app.api.v1.explanation import router as explanation_router
from app.api.v1.explore import router as explore_router
from app.api.v1.health import router as health_router
from app.api.v1.personality import router as personality_router
from app.api.v1.portrait import router as portrait_router
from app.api.v1.similarity import router as similarity_router
from app.api.v1.stories import router as stories_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.startup_checks import run_startup_checks

settings = get_settings()
configure_logging(settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (environment=%s, require_ml_models=%s)",
        settings.app_name,
        settings.environment,
        settings.require_ml_models,
    )
    run_startup_checks(settings)
    yield


app = FastAPI(
    title=settings.app_name,
    description="Every cat has a story.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

# Local dev image storage (see app/storage/) served back out directly —
# cat photos aren't secret, only the analysis data around them is
# access-controlled. Directory is created on first write if missing.
app.mount(
    "/media", StaticFiles(directory=settings.image_storage_dir, check_dir=False), name="media"
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analyses_router)
app.include_router(stories_router)
app.include_router(collection_router)
app.include_router(similarity_router)
app.include_router(explanation_router)
app.include_router(personality_router)
app.include_router(portrait_router)
app.include_router(explore_router)
