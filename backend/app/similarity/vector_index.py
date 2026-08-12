import logging
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class VectorIndex(ABC):
    """Abstraction over "where normalized embedding vectors live and
    how they're searched" (Phase 11 spec §6). `FAISSVectorIndex` is the
    only implementation today; the interface is shaped so a future
    `PgVectorIndex` (embeddings stored in Postgres via the `pgvector`
    extension, queried with `<=>`/`<#>` operators) could replace it
    without `SimilarityService` or anything above it changing — same
    "swap the implementation, not the caller" pattern as
    `ImageStorageProvider` (Phase 9) and `RateLimiter` (Phase 9).

    All vectors passed in are assumed already L2-normalized by the
    caller (`EmbeddingModel.predict` does this at the source) — this
    interface doesn't normalize, it just stores and searches.
    """

    @abstractmethod
    def add(self, vector_id: int, vector: np.ndarray) -> None:
        """Inserts one vector under `vector_id`. Persists immediately
        (write-through) so the index survives an unclean process exit —
        see the class docstring on `FAISSVectorIndex` for the tradeoff
        this makes."""

    @abstractmethod
    def remove(self, vector_id: int) -> None:
        """No-ops if `vector_id` isn't present — callers (the
        reference-counted removal in `embedding_service.py`) already
        decide *whether* to call this; the index itself doesn't need to
        error on "already gone."""

    @abstractmethod
    def search(self, query: np.ndarray, k: int) -> list[tuple[int, float]]:
        """Returns up to `k` `(vector_id, score)` pairs, sorted by
        score descending. `score` is the raw metric this index computes
        (inner product on normalized vectors == cosine similarity for
        `FAISSVectorIndex`) — the caller is responsible for whatever
        that metric means, this layer doesn't relabel it."""

    @abstractmethod
    def get_vector(self, vector_id: int) -> np.ndarray | None:
        """Reconstructs a previously-added vector by id — this is how
        `SimilarityService` gets a *query* vector for "find cats similar
        to analysis X" without ever storing the raw 576 floats anywhere
        else (Postgres included, per Phase 11 spec §33's storage
        caution): the flat index already keeps the exact vectors, this
        just reads one back out. Returns `None` if `vector_id` isn't
        present."""

    @abstractmethod
    def rebuild(self, vectors: list[tuple[int, np.ndarray]]) -> None:
        """Replaces the entire index contents. Used only by the
        `similarity_index` CLI's `rebuild` command — never called from
        a request handler."""

    @abstractmethod
    def save(self) -> None: ...

    @property
    @abstractmethod
    def size(self) -> int: ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """False if the index couldn't be loaded/created — a corrupt
        index file, a dimension mismatch against the configured
        embedding model (Phase 11 spec §21), or FAISS itself not being
        installed. When False, `SimilarityService` must report
        `search_mode: "unavailable"` rather than attempt a search."""


class FAISSVectorIndex(VectorIndex):
    """Exact (brute-force, not approximate) cosine similarity search
    via `faiss.IndexFlatIP` — inner product over L2-normalized vectors
    IS cosine similarity, with no approximation error, which matters
    here: the spec explicitly forbids inventing a similarity number
    that doesn't have a precise mathematical definition, and an
    approximate index (IVF/HNSW) would trade exactness for speed this
    project doesn't need yet at "hundreds or thousands" of vectors
    (spec §22) — `IndexFlatIP` search is O(n·d), a few milliseconds at
    that scale on CPU. Wrapped in `IndexIDMap2` so vectors can be
    addressed by this project's own integer `vector_id` (matching
    `CatEmbeddingModel.vector_id`) instead of FAISS's implicit
    insertion-order indices — which is also what makes both `remove()`
    and `get_vector()` possible at all (a plain `IndexFlatIP` has no
    notion of "id", and the older `IndexIDMap` supports `add`/`search`/
    `remove` but not `reconstruct` — confirmed by hitting
    "reconstruct not implemented for this type of index" directly
    while building this; `IndexIDMap2` specifically adds the reverse
    map that makes reconstruction-by-id work).

    Persistence is write-through: every `add`/`remove` immediately
    calls `faiss.write_index`. At this project's target scale (a few
    thousand 576-dim float32 vectors ≈ a few MB) rewriting the whole
    file on every mutation is cheap and guarantees "survives an
    unclean restart" (spec §7) without needing a WAL or a clean-shutdown
    hook — a real production deployment at much larger scale would
    batch/debounce this instead; documented as a known simplification,
    not an oversight.
    """

    def __init__(self, dimension: int, index_path: str) -> None:
        self._dimension = dimension
        self._path = Path(index_path)
        self._index = None
        self._available = False
        self._load_or_create()

    def _load_or_create(self) -> None:
        try:
            import faiss
        except ImportError:
            logger.warning("faiss not installed — visual similarity search unavailable.")
            return

        if self._path.exists():
            try:
                index = faiss.read_index(str(self._path))
            except Exception:
                logger.error(
                    "Failed to read similarity index at %s — treating as unavailable "
                    "rather than silently starting an empty one (Phase 11 spec §21: "
                    "fail safely, never return incorrect results).",
                    self._path,
                    exc_info=True,
                )
                return

            if index.d != self._dimension:
                logger.error(
                    "Similarity index dimension mismatch: index has d=%d, current "
                    "embedding model expects d=%d — refusing to use it. Run the "
                    "`similarity_index rebuild` CLI command to re-embed everything "
                    "with the current model.",
                    index.d,
                    self._dimension,
                )
                return

            self._index = index
        else:
            self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(self._dimension))

        self._available = True

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def size(self) -> int:
        return int(self._index.ntotal) if self._available else 0

    def add(self, vector_id: int, vector: np.ndarray) -> None:
        if not self._available:
            raise RuntimeError("FAISSVectorIndex.add called while is_available=False")
        vectors = np.asarray([vector], dtype=np.float32)
        ids = np.asarray([vector_id], dtype=np.int64)
        self._index.add_with_ids(vectors, ids)
        self.save()

    def remove(self, vector_id: int) -> None:
        if not self._available:
            raise RuntimeError("FAISSVectorIndex.remove called while is_available=False")
        import faiss

        selector = faiss.IDSelectorArray(np.asarray([vector_id], dtype=np.int64))
        self._index.remove_ids(selector)
        self.save()

    def search(self, query: np.ndarray, k: int) -> list[tuple[int, float]]:
        if not self._available or self._index.ntotal == 0:
            return []
        k_effective = min(k, self._index.ntotal)
        query_batch = np.asarray([query], dtype=np.float32)
        scores, ids = self._index.search(query_batch, k_effective)
        return [
            (int(vector_id), float(score))
            for vector_id, score in zip(ids[0], scores[0], strict=True)
            if vector_id != -1  # FAISS pads short result rows with -1
        ]

    def get_vector(self, vector_id: int) -> np.ndarray | None:
        if not self._available:
            return None
        try:
            return np.asarray(self._index.reconstruct(int(vector_id)), dtype=np.float32)
        except RuntimeError:
            # FAISS raises (not returns None) for an unknown id.
            return None

    def rebuild(self, vectors: list[tuple[int, np.ndarray]]) -> None:
        import faiss

        fresh = faiss.IndexIDMap2(faiss.IndexFlatIP(self._dimension))
        if vectors:
            matrix = np.asarray([v for _, v in vectors], dtype=np.float32)
            ids = np.asarray([vid for vid, _ in vectors], dtype=np.int64)
            fresh.add_with_ids(matrix, ids)
        self._index = fresh
        self._available = True
        self.save()

    def save(self) -> None:
        if not self._available:
            return
        import faiss

        self._path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._path))


_index: FAISSVectorIndex | None = None


def get_vector_index() -> FAISSVectorIndex:
    """Process-wide singleton — same reasoning as the embedding model
    and breed classifier: loading (reading the persisted index file)
    should only happen once per process, and every request must share
    the same in-memory index rather than each reloading it from disk."""
    global _index
    if _index is None:
        from app.core.config import get_settings
        from app.ml.embedding_model import EMBEDDING_DIM

        settings = get_settings()
        _index = FAISSVectorIndex(EMBEDDING_DIM, settings.similarity_index_path)
    return _index
