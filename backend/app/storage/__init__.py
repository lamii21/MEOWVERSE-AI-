from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import ImageStorageProvider
from app.storage.local import LocalImageStorageProvider
from app.storage.s3 import S3ImageStorageProvider


@lru_cache
def get_image_storage() -> ImageStorageProvider:
    settings = get_settings()
    if settings.image_storage_provider == "local":
        return LocalImageStorageProvider(settings.image_storage_dir)
    if settings.image_storage_provider == "s3":
        return S3ImageStorageProvider(
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            public_url_base=settings.s3_public_url_base,
        )
    raise ValueError(f"Unknown image_storage_provider: {settings.image_storage_provider!r}")
