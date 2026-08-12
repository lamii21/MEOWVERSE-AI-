# MeowVerse AI — Project Status

_Last updated: 2026-08-12_

## Current Phase

**Phase 11 — MeowVerse Similarity Engine: Visual Embeddings & Cat
Discovery: complete and verified end-to-end.** Phase 12 is next, not
yet started.

## What Exists

- `backend/` —
  - `app/ml/embedding_model.py` — `EmbeddingModel`, a real
    ImageNet-pretrained `mobilenet_v3_small` (NOT this project's own
    breed-fine-tuned weights) used purely as a feature extractor:
    `predict()` runs `features` + `avgpool` and stops before the
    classification head, returning a 576-dim, L2-normalized `float32`
    vector. Same honest-fallback contract as every other model here —
    `is_available=False` (never a fake/random vector) if torch isn't
    installed or the pretrained weights can't load.
  - `app/similarity/vector_index.py` — `VectorIndex` ABC +
    `FAISSVectorIndex` (`faiss.IndexIDMap2(faiss.IndexFlatIP(576))`,
    exact cosine similarity via inner product on normalized vectors).
    Write-through persistence to `data/similarity_index.faiss`; a
    dimension mismatch or corrupt file on load marks it unavailable
    rather than silently wrong or crashing.
  - `app/models/embedding.py` — `CatEmbeddingModel`: maps one analysis
    to a FAISS `vector_id` + a sha256 `content_hash` + the
    `embedding_model`/`embedding_version`/`embedding_dim` that
    produced it. The raw vector itself is never stored in Postgres —
    only in the FAISS index, reconstructed by id when needed.
  - `app/repositories/embedding_repository.py` — content-hash dedup
    lookup, vector_id reverse-mapping, reference-count for safe
    removal, a simple monotonic `vector_id` counter.
  - `app/services/embedding_service.py` — `embed_and_index`: hashes
    the image, reuses an existing vector for identical content instead
    of re-embedding, otherwise runs the model and adds to the index.
    Best-effort — a failure here never fails the analyze request.
  - `app/services/similarity_service.py` — `find_similar_cats`: the
    one place similarity logic lives. Resolves + authorizes the source
    cat → reconstructs its query vector from FAISS → over-fetches
    candidates → resolves them back to real rows → applies privacy
    (public OR caller-owned) + self-exclusion + optional
    breed/rarity/favorite filters → truncates to k → builds the
    response. Returns `search_mode: "unavailable"` (never fabricates)
    when the model, index, or this specific cat's embedding isn't
    available.
  - `app/schemas/similarity.py` — `SimilarCat` (analysis_id, cat_name,
    image_url, breed, rarity, `visual_similarity` [0-1, clamped ≥0],
    shared_colors, is_favorite [owner-gated], created_at),
    `SimilarityResponse` (source_cat, similar_cats, search_mode,
    embedding_model).
  - `app/api/v1/similarity.py` — `GET
    /api/v1/analyses/{id}/similar?k=&breed=&rarity=&favorites_only=`.
    `k` hard-capped at 20 by the query parameter's own validation.
  - `app/cli/similarity_index.py` — `build`/`rebuild`/`verify`, dev/
    admin-only, never HTTP-exposed. `verify` checks for duplicate
    mappings, missing analysis records, stale model/version rows,
    dimension mismatches, and orphaned vectors — reports and exits
    non-zero, never silently repairs.
  - `app/__init__.py` — now sets `KMP_DUPLICATE_LIB_OK=TRUE` before
    anything else in the package can import torch or faiss (see Errors
    below — a real crash, not a hypothetical).
  - `app/services/analysis_service.py` — `analyze_image` now also
    computes and indexes an embedding (its own try/except, separate
    from analysis persistence, so an embedding failure is never
    conflated with an analysis-save failure in logs).
  - `app/schemas/analysis.py` — the previously-stubbed
    `embedding_available: bool` field (present since early phases,
    always `False`) is now real: `True` exactly when this analysis's
    embedding was actually computed and indexed.
  - Migration `8903bf7a8de1` — adds `cat_embeddings` only; no changes
    to any existing table. Verified via upgrade → downgrade → upgrade.
  - Tests: `test_embedding_model.py` (dimension, L2-normalization,
    determinism, dtype), `test_vector_index.py` (controlled-vector
    math: identical/orthogonal/opposite/ranked-distance vectors per
    spec §28 — not just HTTP assertions — plus persistence, corruption,
    dimension-mismatch, remove/reconstruct), `test_embedding_service.py`
    (hash determinism, duplicate-content dedup, graceful degradation),
    `test_similarity.py` (self-exclusion, k-capping, ordering, privacy
    across guest/owner/stranger, duplicate-image near-1.0 matching,
    post-retrieval filters). **211/211 backend tests passing** (was
    170), ruff clean.
- `frontend/` —
  - `types/similarity.ts`, `services/similarity.ts` — typed client for
    the endpoint above.
  - `features/similarity/components/SimilarCatCard.tsx` — compact
    result tile (image, name, breed, rarity, "N% visually similar").
  - `features/similarity/components/CatsLikeThis.tsx` — the "Cats Like
    This 🐾" section: a rotating cute loading message, an honest
    "Your cat might be one of a kind. 🐾" empty state (only shown when
    the search genuinely ran and found nothing), a distinct
    "unavailable" message when the model/index isn't ready, real error
    handling, and the results grid.
  - `features/similarity/components/HowSimilarityWorks.tsx` —
    collapsed-by-default 4-step technical explainer (spec §36).
  - Wired into three places (spec §16/§19): the analyze results page
    (`ResultExperience.tsx`), the public `/cat/[id]` page
    (`PublicCatView.tsx`), and the owner's `/collection/[id]` page.
    Implemented as an always-visible auto-loading section rather than
    a separate "Find Similar Cats" button — the results are already
    there without an extra click; documented as a deliberate UX choice
    naming the same underlying reusable component.
  - 3 new test files (`SimilarCatCard.test.tsx`, `CatsLikeThis.test.tsx`
    covering loading/empty/unavailable/error/success/real-percentage
    states). **96/96 frontend tests passing** (was 85), lint/build
    clean.

## Real Results (Phase 11)

- **Both suites green**: 211/211 backend (pytest, real Postgres, real
  torch/FAISS inference — no mocks), 96/96 frontend.
- **The `similarity_index` CLI was run for real** against this
  project's own accumulated dev database (not a toy dataset): `build`
  backfilled embeddings for 869 previously-unembedded analyses (real
  photos already on disk from earlier phases' testing);
  `verify` afterward reported **980 embedding rows, index size 24
  distinct vectors, zero problems found**.
- **Qualitative validation with real photos** (Phase 11 spec §30) —
  4 breeds × 3 real Oxford-IIIT Pet photos each (Sphynx, Persian,
  Bengal, Russian Blue; the same dataset this project's own breed
  classifier was trained on, already present in the repo), first-3-
  alphabetical per breed, **not hand-picked for a flattering result**.
  Same-breed images landed in each other's top-3 nearest neighbors in
  18 of 36 possible neighbor slots — well above chance, and Persian
  images clustered especially tightly (0.82-0.86 cosine similarity,
  consistent with their visually distinctive long white coat).
  Reported honestly alongside the imperfect cases: one Bengal image
  didn't rank any other Bengal in its own top-3, and Sphynx/Russian
  Blue cross-matched somewhat (both are short/bare-coated, plain-
  colored cats — a visually defensible confusion, not a bug). This is
  a qualitative sanity check over 12 images, explicitly **not** a
  formal retrieval benchmark.
- **Performance, measured, not estimated**:
  - Embedding generation: mean 73.6ms, range 60.6-101.9ms (n=12,
    single-threaded CPU inference, warm process).
  - FAISS search: mean 0.886ms, p95 0.966ms (k=20, 24 real indexed
    vectors, warm process).
  - Full `POST /api/v1/analyses` (breed + colors + profile + embed +
    persist), warm process: 1.24s.
  - Full `GET /api/v1/analyses/{id}/similar` end-to-end (DB round-trips
    + FAISS search + privacy filtering), warm process: mean ~370ms
    over 10 requests (335-568ms range) — DB round-trip overhead
    dominates this, not the sub-millisecond FAISS search itself; noted
    as a real, honest number, not a target.
  - A cold process pays a one-time ~40s `import torch` cost on its
    *first* embedding-touching request (confirmed directly, twice) —
    the process-wide singleton pattern (matching `get_breed_classifier`)
    means every request after that first one is warm.
- **Verified end-to-end via a live, scripted Playwright run** (14
  steps, real photos, real dev servers): register → create 4 real cat
  analyses (3 Persians + 1 Sphynx) → confirm all 4 got real embeddings
  → open a Persian's Cat Card → the "Cats Like This" section loads
  real results (the other 2 Persians at 86%/84%, the Sphynx at 58%,
  three unrelated cats at 0%) → confirm the source cat is excluded →
  confirm descending similarity order in both the API and the
  rendered UI → confirm a second, stranger user gets a 404 trying to
  query the first user's private cat → confirm a brand-new user's
  brand-new cat correctly gets a real (not hardcoded) empty/results
  state → click into a similar cat and back → refresh and confirm
  results persist. All 14 steps passed, **zero console errors**.
- **Responsive** (320/375/768/1440px) and **reduced-motion** verified
  on a real page with "Cats Like This" rendered — zero horizontal
  overflow, zero console errors under `prefers-reduced-motion`.

## Two Real Bugs Found and Fixed This Phase

1. **torch + faiss-cpu OpenMP conflict, a hard process crash.** Both
   bundle their own copy of Intel's OpenMP runtime on Windows; loading
   both in one process aborts the interpreter outright
   (`Fatal Python error: Aborted`) the moment the second one is
   imported — hit directly while running `test_vector_index.py`
   (imports faiss) followed by `test_embedding_model.py` (imports
   torch) in the same pytest session. Fixed with the standard,
   documented workaround (`KMP_DUPLICATE_LIB_OK=TRUE`), set in
   `app/__init__.py` — the one place guaranteed to run before any
   `app.*` submodule, so the production app, every test, and the CLI
   are all covered with no import-order race.
2. **`faiss.IndexIDMap` doesn't support `reconstruct()`.** Confirmed
   directly (`RuntimeError: reconstruct not implemented for this type
   of index`) — the plain ID-mapping wrapper supports add/search/remove
   but not reconstruction-by-id at all. Switched to `IndexIDMap2`,
   which maintains the reverse map that makes it work. Found before
   this ever reached a real request, via the vector-index unit tests.

## What Does Not Exist Yet

Grad-CAM explainability (Phase 12), image generation (Phase 13),
advanced analytics, a mobile app, a social feed, chat, OAuth login,
pgvector (the `VectorIndex` interface is ready for it, deliberately
not introduced since nothing requires it yet), a formal retrieval
benchmark (no reliable ground truth exists — see below), deleting an
analysis (and therefore no caller of `embedding_service
.remove_from_index` yet, though it's implemented and tested). See
ROADMAP.md Phases 12–17.

## Known Limitations / Honest Gaps

- **No formal retrieval benchmark was performed** (Phase 11 spec §31)
  — same-breed retrieval-rate@K would conflate breed classification
  with visual similarity, which this phase's own spec explicitly
  warns against treating as equivalent. The qualitative validation
  above is real and honestly reported, but it is not a benchmark.
- **Single global FAISS index, not per-user/public-vs-private
  indexes** — a deliberate architecture choice (see ARCHITECTURE.md
  §21): privacy is enforced as a mandatory, unconditional SQL filter
  at the `SimilarityService` layer instead, the same pattern this
  codebase already uses for every other ownership check. Documented
  as the reason this is still safe despite one shared index.
- **Single-process-instance limitation**, same as the in-memory rate
  limiter (Phase 9) and this project's other process-wide singletons:
  the FAISS index and embedding model are in-memory per process; a
  multi-worker deployment would need either a shared index server or
  per-worker index files kept in sync.
- **Write-through index persistence** rewrites the whole index file on
  every add/remove — cheap at this project's scale (a few MB), would
  need batching at real production scale.
- **`GET /similar`'s ~370ms average is dominated by sequential DB
  round-trips**, not the sub-millisecond FAISS search — a real,
  measured number, left as-is rather than prematurely optimized
  (batching the candidate-resolution queries is the obvious next
  step if this ever needs to be faster).
- Previously noted limitations (rate limiting in-memory, local-disk
  image storage, client-side-only route protection, the one
  architecturally-unavoidable guest 401, no live Anthropic API call
  tested, local dev Postgres on port 5433, the ML-less Docker image,
  `vitest.config.ts`'s `pool: "threads"`) are unchanged from Phase 9/10.

## Next Steps

Begin Phase 12: Grad-CAM Explainability (heatmap generation for the
breed classifier, a "why did the AI predict this?" UI panel) — the
next un-started item in ROADMAP.md.

## Notes for Future Sessions

- **torch and faiss-cpu cannot both be imported in the same Windows
  process without `KMP_DUPLICATE_LIB_OK=TRUE` set first** — set it as
  early as possible (this project sets it in `app/__init__.py`) if any
  future phase adds another OpenMP-linked library (e.g. a new
  torch-based model) to a process that already imports faiss, or
  vice versa.
- **`faiss.IndexIDMap` ≠ `faiss.IndexIDMap2`** — only the latter
  supports `reconstruct()`. If a future vector index needs "get this
  exact vector back by id," reach for `IndexIDMap2` from the start.
- **A generic ImageNet-pretrained backbone, not this project's own
  fine-tuned classifier, is the right embedding source when the goal
  is visual similarity, not classification** — a fine-tuned model's
  features are pulled toward its training objective (breed
  separation) at the expense of general visual structure. Worth
  remembering as a category, not just a one-off choice, if a future
  phase needs embeddings for a different purpose.
- **Reusing an existing model's penultimate-layer features (not
  training a new model) is a legitimate, standard way to get a strong
  embedding baseline** — validated qualitatively with real photos
  before committing to it as the shipped approach.
- Previously noted lessons (Base UI quirks, dark-mode media-query
  strategy, forced-tool-use for structured LLM output, the
  `useSyncExternalStore` pattern for SSR-safe external state, DB-backed
  sessions over JWT, ownership-scoped queries as the security boundary,
  the `AuthCard` reduced-motion hydration fix, the idempotent-event-log
  pattern for un-farmable rewards) all still apply.
