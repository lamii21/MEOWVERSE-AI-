from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.analyses import router as analyses_router
from app.api.v1.auth import router as auth_router
from app.api.v1.collection import router as collection_router
from app.api.v1.health import router as health_router
from app.api.v1.similarity import router as similarity_router
from app.api.v1.stories import router as stories_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.debug)

app = FastAPI(
    title=settings.app_name,
    description="Every cat has a story.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
