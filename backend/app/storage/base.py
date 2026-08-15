from abc import ABC, abstractmethod


class ImageStorageProvider(ABC):
    """Abstraction over where uploaded cat photos live (Phase 9). Not
    hard-coded to one backend — `LocalImageStorageProvider` (disk, for
    local dev) is the only implementation today, but the interface is
    shaped so an S3-compatible provider is a drop-in swap later: same
    `save`/`delete` contract, no caller changes. Credentials for
    whatever backend is configured live only in backend env vars/config
    — this interface never accepts or returns them, so there is nothing
    for the frontend to accidentally receive.
    """

    @abstractmethod
    async def save(self, image_bytes: bytes, *, key: str, content_type: str) -> str:
        """Persists the image and returns a URL the frontend can load
        it from directly (no further auth needed to view it — cat
        photos aren't secret, only the surrounding analysis data is
        access-controlled)."""

    @abstractmethod
    async def load(self, url: str) -> bytes | None:
        """Reverses `save`'s URL back into the original bytes — added
        in Phase 12 for Grad-CAM, which needs the actual uploaded photo
        (not just its URL) to run inference on. Returns `None` if the
        file can't be found/read (never raises for that) — same
        best-effort philosophy as `save`. An S3-compatible provider
        would implement this as a GET against the object store."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """False if this provider can't currently accept writes (e.g. the
        configured directory isn't writable). Persisting an image must
        never be allowed to crash the analyze endpoint — callers treat a
        save failure exactly like the existing best-effort DB write."""
