from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import ImageStorageProvider
from app.storage.local import LocalImageStorageProvider


@lru_cache
def get_image_storage() -> ImageStorageProvider:
    settings = get_settings()
    # Only "local" exists today; the ABC is what a future S3-compatible
    # provider would implement — see app/storage/base.py.
    if settings.image_storage_provider == "local":
        return LocalImageStorageProvider(settings.image_storage_dir)
    raise ValueError(f"Unknown image_storage_provider: {settings.image_storage_provider!r}")
