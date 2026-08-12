"""Development/admin tooling for the visual-similarity index (Phase 11
spec §20) — deliberately never exposed over HTTP, never callable by a
normal user. Run from `backend/` with the project venv active:

    python -m app.cli.similarity_index build     # embed analyses that don't have one yet
    python -m app.cli.similarity_index rebuild    # re-embed everything from scratch
    python -m app.cli.similarity_index verify     # consistency checks, exit 1 if any fail
"""

import argparse
import asyncio
import io
import sys
from pathlib import Path

from PIL import Image
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.ml.embedding_model import get_embedding_model
from app.models.analysis import CatAnalysisModel
from app.repositories import embedding_repository
from app.repositories.analysis_repository import get_many_by_ids
from app.services.embedding_service import embed_and_index
from app.similarity.vector_index import get_vector_index


def _read_local_image_bytes(image_url: str) -> bytes | None:
    """Reverses `LocalImageStorageProvider`'s `/media/{filename}` URL
    back to a filesystem path — only works for the local storage
    backend. A future S3-backed provider would need this CLI updated to
    fetch over the SDK instead; that's a known limitation of this dev
    tool, not of the architecture (`SimilarityService` itself never
    needs to re-read a stored image, only this backfill/rebuild tool
    does, since embeddings are normally computed once at analyze time).
    """
    settings = get_settings()
    if not image_url.startswith("/media/"):
        return None
    path = Path(settings.image_storage_dir) / image_url.removeprefix("/media/")
    if not path.exists():
        return None
    return path.read_bytes()


async def build(*, force: bool) -> None:
    async with async_session_factory() as db:
        if force:
            print("Clearing existing embedding rows and vector index...")
            for row in await embedding_repository.list_all(db):
                await db.delete(row)
            await db.commit()
            get_vector_index().rebuild([])

        stmt = select(CatAnalysisModel).where(CatAnalysisModel.image_url.is_not(None))
        analyses = list((await db.execute(stmt)).scalars().all())

        embedded = skipped_existing = skipped_no_image = failed = 0
        for row in analyses:
            if not force and await embedding_repository.get_by_analysis_id(db, row.id) is not None:
                skipped_existing += 1
                continue

            image_bytes = _read_local_image_bytes(row.image_url)
            if image_bytes is None:
                skipped_no_image += 1
                continue

            try:
                image = Image.open(io.BytesIO(image_bytes))
                image.load()
            except Exception:
                failed += 1
                continue

            embedding_row, latency = await embed_and_index(db, row.id, image, image_bytes)
            if embedding_row is None:
                failed += 1
            else:
                embedded += 1
                print(f"  embedded analysis_id={row.id} in {latency * 1000:.1f}ms")

        print(
            f"Done. embedded={embedded} skipped_existing={skipped_existing} "
            f"skipped_no_image={skipped_no_image} failed={failed} "
            f"total_analyses_with_photo={len(analyses)}"
        )


async def verify() -> None:
    """Consistency checks (Phase 11 spec §21) — reports problems, never
    silently repairs them (a silent repair would hide exactly the kind
    of bug this command exists to surface)."""
    settings = get_settings()
    model = get_embedding_model()
    problems: list[str] = []

    async with async_session_factory() as db:
        rows = await embedding_repository.list_all(db)

        seen_analysis_ids: set = set()
        for row in rows:
            if row.analysis_id in seen_analysis_ids:
                problems.append(f"duplicate mapping: analysis_id={row.analysis_id} appears twice")
            seen_analysis_ids.add(row.analysis_id)

        existing_analyses = {
            a.id for a in await get_many_by_ids(db, [row.analysis_id for row in rows])
        }
        for row in rows:
            if row.analysis_id not in existing_analyses:
                problems.append(
                    f"missing analysis record: cat_embeddings row {row.id} references "
                    f"nonexistent analysis_id={row.analysis_id}"
                )
            if row.embedding_model != model.name or row.embedding_version != model.version:
                problems.append(
                    f"stale embedding: analysis_id={row.analysis_id} was embedded with "
                    f"{row.embedding_model}:{row.embedding_version}, current model is "
                    f"{model.name}:{model.version} — run `rebuild` to fix"
                )
            if row.embedding_dim != model.dimension:
                problems.append(
                    f"dimension mismatch: analysis_id={row.analysis_id} has "
                    f"embedding_dim={row.embedding_dim}, current model dimension="
                    f"{model.dimension}"
                )

        index = get_vector_index()
        if not index.is_available:
            problems.append(
                f"vector index unavailable at {settings.similarity_index_path} — see "
                "logs for why (a missing file is fine on a fresh install; a load or "
                "dimension error found at startup is not)"
            )
        else:
            db_vector_ids = {row.vector_id for row in rows}
            for vector_id in db_vector_ids:
                if index.get_vector(vector_id) is None:
                    problems.append(
                        f"orphan mapping: cat_embeddings references vector_id={vector_id} "
                        "which is not present in the FAISS index"
                    )
            if index.size > len(db_vector_ids):
                problems.append(
                    f"orphan vectors: FAISS index has {index.size} vectors but only "
                    f"{len(db_vector_ids)} distinct vector_ids are referenced from Postgres"
                )

    if problems:
        print(f"FOUND {len(problems)} PROBLEM(S):")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)

    print(
        f"OK — {len(rows)} embedding rows, index size {get_vector_index().size}, "
        "no problems found."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "rebuild", "verify"])
    args = parser.parse_args()

    if args.command == "build":
        asyncio.run(build(force=False))
    elif args.command == "rebuild":
        asyncio.run(build(force=True))
    elif args.command == "verify":
        asyncio.run(verify())


if __name__ == "__main__":
    main()
