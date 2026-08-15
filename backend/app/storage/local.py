import logging
from pathlib import Path

from app.storage.base import ImageStorageProvider

logger = logging.getLogger(__name__)

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class LocalImageStorageProvider(ImageStorageProvider):
    """Disk-backed storage for local development — writes under
    `<directory>/`, served back out via a static file mount at `/media`
    (see app/main.py). Not suitable for a real multi-instance
    deployment (the disk isn't shared), which is exactly the gap the
    `ImageStorageProvider` abstraction exists to let a later
    S3-compatible implementation fill without touching any caller.
    """

    def __init__(self, directory: str) -> None:
        self._directory = Path(directory)

    @property
    def is_available(self) -> bool:
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            logger.warning("Local image storage directory is not writable", exc_info=True)
            return False

    async def save(self, image_bytes: bytes, *, key: str, content_type: str) -> str:
        extension = _EXTENSION_BY_CONTENT_TYPE.get(content_type, "bin")
        filename = f"{key}.{extension}"
        self._directory.mkdir(parents=True, exist_ok=True)
        (self._directory / filename).write_bytes(image_bytes)
        return f"/media/{filename}"

    async def load(self, url: str) -> bytes | None:
        if not url.startswith("/media/"):
            return None
        path = self._directory / url.removeprefix("/media/")
        try:
            # Guard against path traversal (`/media/../../etc/passwd`)
            # escaping the storage directory — resolve() collapses any
            # `..` segments, then confirm the result is still inside
            # `self._directory` before ever reading it.
            resolved = path.resolve()
            if not resolved.is_relative_to(self._directory.resolve()):
                return None
            return resolved.read_bytes()
        except OSError:
            return None
