import logging

from app.storage.base import ImageStorageProvider

logger = logging.getLogger(__name__)

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class S3ImageStorageProvider(ImageStorageProvider):
    """Object-storage-backed implementation of `ImageStorageProvider`
    (Phase 17) — the production counterpart to `LocalImageStorageProvider`,
    filling the exact gap that abstraction was built for (Phase 9): a
    container's local disk doesn't survive a redeploy or scale past one
    instance, so uploaded photos, Grad-CAM overlays, and AI portraits
    need to live somewhere shared and durable instead.

    Works with AWS S3 directly, or any S3-compatible provider
    (Cloudflare R2, Backblaze B2, DigitalOcean Spaces, MinIO for local
    testing) via `endpoint_url` — nothing here is AWS-specific beyond
    using the same `boto3` client every one of those providers supports.
    `save`/`load`'s contract (bytes in, a URL out; that same URL back
    into bytes) is identical to the local provider's — no caller in
    `app/services/` needed to change to support this.
    """

    def __init__(
        self,
        *,
        bucket_name: str,
        region: str,
        endpoint_url: str | None,
        access_key_id: str | None,
        secret_access_key: str | None,
        public_url_base: str | None,
    ) -> None:
        self._bucket_name = bucket_name
        self._region = region
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        # If unset, falls back to the bucket's own virtual-hosted-style
        # URL — fine for AWS S3 with public read access, but most real
        # deployments front the bucket with a CDN/custom domain instead,
        # which is exactly what this lets you point at.
        self._public_url_base = (public_url_base or "").rstrip("/")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3",
                region_name=self._region,
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
            )
        return self._client

    @property
    def is_available(self) -> bool:
        try:
            import boto3  # noqa: F401
        except ImportError:
            logger.warning("boto3 not installed — S3 image storage unavailable.")
            return False
        if not self._bucket_name:
            logger.warning("No S3 bucket configured — S3 image storage unavailable.")
            return False
        return True

    def _public_url(self, key: str) -> str:
        if self._public_url_base:
            return f"{self._public_url_base}/{key}"
        if self._endpoint_url:
            return f"{self._endpoint_url.rstrip('/')}/{self._bucket_name}/{key}"
        return f"https://{self._bucket_name}.s3.{self._region}.amazonaws.com/{key}"

    async def save(self, image_bytes: bytes, *, key: str, content_type: str) -> str:
        extension = _EXTENSION_BY_CONTENT_TYPE.get(content_type, "bin")
        object_key = f"{key}.{extension}"
        client = self._get_client()
        # boto3 is sync; called from async endpoints the same best-effort
        # way `LocalImageStorageProvider.save` is (Phase 9's philosophy:
        # a storage failure must never fail the analyze request) — a
        # thread-pool executor would avoid blocking the event loop under
        # real concurrent load, a scoped follow-up if/when that's
        # measured to matter, not assumed upfront.
        client.put_object(
            Bucket=self._bucket_name,
            Key=object_key,
            Body=image_bytes,
            ContentType=content_type,
        )
        return self._public_url(object_key)

    async def load(self, url: str) -> bytes | None:
        prefix = f"{self._public_url_base}/" if self._public_url_base else None
        if prefix and url.startswith(prefix):
            object_key = url.removeprefix(prefix)
        elif f"/{self._bucket_name}/" in url:
            object_key = url.split(f"/{self._bucket_name}/", 1)[1]
        else:
            return None

        try:
            client = self._get_client()
            response = client.get_object(Bucket=self._bucket_name, Key=object_key)
            return response["Body"].read()
        except Exception:
            logger.warning("Failed to load %r from S3 storage", url, exc_info=True)
            return None
