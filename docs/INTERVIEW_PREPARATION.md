# MeowVerse — Technical Interview Preparation

Real questions grounded in the actual implementation, organized by
category. Every answer references a real file/decision in this
repository — not a generic textbook answer.

---

## Machine Learning

**Q: Why MobileNetV3-Small?**
A: It's a good fit for a CPU-only training/inference budget (no CUDA
wheel was practical for this project's bandwidth — see
`requirements-ml.txt`'s comment) while still being a real, modern
architecture with strong ImageNet pretrained weights available in
`torchvision`. For a 12-class fine-tuning task on ~2,400 images, a
larger backbone (ResNet50, EfficientNet) would be slower to train and
serve with no accuracy benefit at this dataset size, and would make
Docker image size and CPU inference latency worse for no real gain.

**Q: Why transfer learning instead of training from scratch?**
A: 2,371 images is far too small to train a CNN from random
initialization without severe overfitting. ImageNet pretraining gives
the model general visual features (edges, textures, shapes) for free;
fine-tuning only needs to adapt those features to the 12-breed
classification task, which is realistic at this dataset size — and
it's what actually got 87.5% top-1 / 98.6% top-3 accuracy on a genuine
held-out test set (`ml/evaluation/evaluate.py`, re-verified
independently in Phase 16 with byte-identical results).

**Q: How do you know the model isn't overfitting?**
A: Held-out train/val/test split (70/15/15, seed=42) with zero
filename overlap between splits, verified directly via a set
intersection check (not assumed) during the Phase 16 validation pass.
Test accuracy (87.5%) is measured on images the model never saw during
training or hyperparameter selection.

**Q: What's the confidence calibration like?**
A: Measured, not assumed: a real accuracy-by-confidence-bucket
analysis found **4.4% of test predictions were confidently (≥80%)
wrong** — a genuine, reported calibration gap, not smoothed over. See
`AI_VALIDATION_REPORT.md` §6.

---

## Computer Vision

**Q: Why does fur color analysis use GrabCut instead of just
clustering the whole image?**
A: Clustering raw pixels without segmentation would let background
color dominate the palette (e.g. a cat photographed on a green lawn
would report "green" as a dominant fur color). GrabCut segments the
likely foreground first, so K-means only clusters pixels that are
actually part of the cat (with a documented fallback to the whole
image if the foreground mask ends up degenerate).

**Q: Is the fur-color output scientifically accurate?**
A: No, and the product says so explicitly — it's documented as a
*visual estimation* (RGB nearest-neighbor against a small reference
palette), not a colorimetrically calibrated measurement. Real-world
lighting/shadow can shift the reading meaningfully (documented in
`PROJECT_STATUS.md` with a real example: a Siamese cat photographed
outdoors read as silver/gray instead of the breed-standard cream, a
legitimate reading of real shadow, not a bug).

**Q: What image validation happens before any model sees the upload?**
A: Content-type allowlist (JPEG/PNG/WebP only), a size cap
(`MAX_UPLOAD_SIZE_MB`), a real decode-and-verify pass via Pillow
(catching corrupted/non-image bytes), a minimum dimension floor, and —
added after finding a real bug — an explicit maximum dimension ceiling
plus a caught `DecompressionBombError`, since a crafted image with
extreme declared dimensions was previously producing an unhandled 500.

---

## Deep Learning

**Q: Why use a separate model for embeddings instead of the fine-tuned
breed classifier's own features?**
A: The breed classifier's features are optimized to *discriminate
between the 12 known breeds* — reusing them for similarity would make
"similar cats" collapse into "same predicted breed," and would offer
nothing for cross-breed visual similarity (two different breeds that
happen to look alike). The embedding model is a second, separately
loaded MobileNetV3-Small using the stock ImageNet weights, deliberately
not fine-tuned, so it captures general visual appearance instead.

**Q: What's the embedding dimensionality and why?**
A: 576-dim, L2-normalized — the natural pooled-feature output size of
MobileNetV3-Small's final block before its classifier head. No
dimensionality reduction is applied; FAISS's `IndexFlatIP` handles
576-dim vectors at this dataset scale without needing approximate
search.

---

## Grad-CAM

**Q: How does Grad-CAM actually work here?**
A: A forward pass through the real classifier produces the predicted
class's logit. A backward pass computes the gradient of that specific
class score with respect to the last convolutional layer's feature
maps (`features[-1]`, verified empirically to produce a `(576,7,7)`
tensor). Those gradients are global-average-pooled into one importance
weight per feature channel, used to weight the feature maps, summed,
passed through ReLU (keeping only features that *positively*
influenced the prediction), normalized to `[0,1]`, resized to the
original image dimensions, and alpha-blended as a heatmap overlay.

**Q: Why implement it from scratch instead of using `pytorch-grad-cam`
(already a project dependency)?**
A: Auditability and testability — every step (hook registration,
gradient capture, weighting, ReLU, normalization) is code I can write
a targeted test against (e.g. "a different target class produces a
different heatmap" — a real gradient-dependence test in the suite),
rather than trusting a black-box library call.

**Q: What does Grad-CAM *not* prove?**
A: It's never described as proof the model is "looking at the cat" or
as a causal explanation of the cat's actual breed — only as "a visual
explanation of regions contributing to the prediction." A separate
faithfulness sanity check (masking the top 15% of the heatmap and
re-measuring confidence) showed a real mean confidence drop, but is
explicitly documented as a sanity check, not proof of causality.

---

## FAISS

**Q: Why FAISS instead of a simpler in-memory brute-force search, or a
managed vector database?**
A: At this dataset's scale (hundreds to low thousands of vectors),
brute-force cosine similarity in pure Python/NumPy would work
correctly but slower; FAISS's `IndexFlatIP` gives the same *exact*
result with a much faster, well-tested C++ implementation, with no
new infrastructure to run (it's an in-process library, not a service).
A managed vector database was explicitly not introduced — the spec for
that phase said not to add one unless existing infrastructure already
required it, and it didn't.

**Q: Approximate or exact search?**
A: Exact — `IndexFlatIP`, not an approximate index (e.g. HNSW/IVF).
At this scale, exact search is fast enough and removes an entire class
of "is this actually the closest match" correctness question.

**Q: How do you handle the index surviving a restart / scaling past
one instance?**
A: The index is a write-through-persisted file
(`similarity_index_path`), rebuilt in-memory on process start from
that file if present. A documented, known limitation: this is a
single-process, single-file design — a multi-instance deployment would
need a shared/rebuilt index per instance, not solved in this project
since it wasn't needed yet.

---

## Embeddings

**Q: Why cosine similarity specifically?**
A: Cosine similarity measures the *angle* between vectors, ignoring
magnitude — appropriate for feature vectors from a CNN where the
direction of the feature representation (which features are "on")
matters more than raw activation magnitude, which can vary with
unrelated factors like image contrast. Implemented as inner product on
L2-normalized vectors, which is mathematically equivalent to cosine
similarity and what `IndexFlatIP` computes directly.

**Q: How did you verify the similarity math is actually correct, not
just "the endpoint returns 200"?**
A: Dedicated controlled-vector tests: identical vectors score exactly
1.0, orthogonal vectors score 0.0, opposite vectors score negative,
and a vector closer to the query always outranks a farther one in
results — see `tests/test_vector_index.py`.

---

## LLMs

**Q: How do you prevent the LLM from changing the breed prediction or
other real signals?**
A: Structurally, not by prompt instruction. The Anthropic integration
uses **forced tool use**: the tool's `input_schema` is generated
directly from the Pydantic response model (e.g. `CatProfile`,
`PersonalityInterpretation`), and those schemas simply have no fields
for breed, color, or trait scores. The model cannot return a value for
something the schema has no slot for — verified by a dedicated test
that the profile response never contains overwritten CV signals.

**Q: What happens if the LLM's response doesn't match the schema?**
A: One semantic retry (`MAX_ATTEMPTS = 2` — one initial call plus one
retry), then falls back to a deterministic, hand-written offline
variant. No unbounded retry loop.

**Q: What happens if no API key is configured?**
A: `NullLLMProvider` — `is_available = False`, and every caller checks
this before attempting a call, falling back to the deterministic demo
path immediately. Verified: the entire product is fully functional
with zero AI keys configured, which is in fact the state of this
development environment right now.

---

## Prompt Engineering

**Q: How is the story-generation prompt structured?**
A: A composable, independently unit-tested prompt builder
(`app/ai/story_prompt.py`) — system rules, explicit safety rules (no
sexual/violent/hateful/dangerous/medical/political content, no
copyrighted characters), per-style tone instructions, and a
cat-context section that explicitly labels which signals are real CV
output versus fictional/creative, so the model never treats its own
invented narrative detail as fact about the cat.

**Q: How do you prevent user-supplied text (portrait customization)
from hijacking the prompt?**
A: It's sanitized (control characters stripped, whitespace collapsed,
length-capped at 120 characters) and structurally confined to its own
labeled "optional creative idea" section of the prompt — verified by a
dedicated prompt-injection test that it cannot reach or override the
identity-preservation/system-rules sections.

---

## Backend

**Q: Why FastAPI?**
A: Async-native (matters for I/O-bound work like calling external AI
APIs and Postgres without blocking), automatic OpenAPI docs generation
from Pydantic models (used directly for the forced-tool-use LLM schema
trick above), and strong typing throughout the request/response
lifecycle.

**Q: How is the codebase layered?**
A: `app/api/` (routers, request/response handling) → `app/services/`
(business logic orchestration) → `app/repositories/` (SQLAlchemy
queries) / `app/ml/` (CV models) / `app/ai/` (LLM/image-gen providers)
/ `app/similarity/` (FAISS). Each layer only calls downward, keeping
routers thin and business logic testable independent of HTTP.

---

## Database

**Q: Why PostgreSQL, and why async SQLAlchemy?**
A: Relational integrity (foreign keys, unique constraints) matters
here — a session must reference a real user, an analysis a real owner,
etc. — and Postgres's JSONB columns handle the semi-structured parts
(personality traits, story content) without needing a second database.
Async SQLAlchemy keeps the request path non-blocking under FastAPI.

**Q: How are migrations handled?**
A: Alembic, one migration per phase, reviewed for safety this project
explicitly (Phase 17): every `NOT NULL` addition to a pre-existing
table used `server_default` or an explicit nullable→backfill→constrain
pattern; every `downgrade()` fully reverses its `upgrade()`. A real
fresh-upgrade → full-downgrade → re-upgrade cycle was verified against
an isolated Postgres container, not just asserted to work.

---

## Authentication

**Q: How do you protect private cats from other users?**
A: SQL-level filtering, never fetch-then-check in application code —
every query for a private resource includes `WHERE user_id = :caller`
(or an equivalent public-OR-owned predicate) directly, so a query
simply cannot return another user's private row. Verified by a
dedicated cross-user privacy regression suite.

**Q: Why DB-backed opaque sessions instead of JWT?**
A: Revocability. A JWT is self-contained and valid until its expiry
regardless of server-side state — revoking one before expiry needs an
extra blocklist/revocation-list system anyway, which is more
complexity for less security than what a DB-backed session already
gives for free: logout deletes the session row, and it's immediately
unusable. Only the session token's *hash* is stored (mirroring
password hashing), so a database leak doesn't hand over usable
sessions either.

**Q: What happens on logout?**
A: `DELETE FROM sessions WHERE token_hash = ...` — the session is
immediately invalid server-side, not just client-side cookie deletion.

---

## Security

**Q: How is CSRF handled?**
A: Primary defense is the session cookie's `SameSite=Lax` attribute —
modern browsers won't attach it to cross-site requests that aren't
top-level navigations. Defense-in-depth on top of that: an
`Origin`-header check on every state-changing authenticated endpoint,
403ing on a mismatch, deliberately not a full double-submit-cookie CSRF
token scheme (judged unnecessary complexity for a same-origin-by-
configuration SPA+API pair with no cross-site form posting anywhere in
the product).

**Q: How do you prevent AI cost abuse?**
A: Server-side rate limiting on every AI-cost-bearing endpoint
(never trusting a frontend button's disabled state), a stricter budget
specifically for the more expensive image-generation endpoint, bounded
prompt sizes, a hard cap on retries (never unbounded), and on-demand
generation with caching/deduplication (repeating an identical request
never triggers a second paid call).

**Q: What image-upload attacks did you specifically test for?**
A: Empty files, wrong/spoofed content-type, corrupted bytes, an
executable disguised with an image content-type (real PE magic bytes,
confirmed rejected because Pillow can't decode it, not because of the
filename or claimed type), decompression bombs, oversized dimensions,
and path-traversal/Unicode filenames (confirmed inert — the
client-supplied filename is never used to construct a storage path at
all; server-generated UUIDs are).

---

## Docker

**Q: What was the biggest Docker-specific problem you hit?**
A: The backend Docker image had been running the entire CV pipeline in
demo mode since early development, because `requirements-ml.txt` was
never installed in the image. Fixing that surfaced two further,
genuinely subtle bugs only discoverable by *running* the built
container: `torch` resolving PyPI's CUDA-bundled wheel on Linux
(3.4GB image) despite the project's own CPU-only intent holding on the
Windows dev machine but not in the container, and a package conflict
between `opencv-python` (transitively pulled by `grad-cam`) and
`opencv-python-headless`, where whichever installed last silently
broke `cv2`'s real functionality on disk.

**Q: How is the image optimized?**
A: Multi-stage build — a `builder` stage with `gcc`/`libpq-dev`
installs everything into a venv; a slim `runtime` stage copies only
that finished venv plus app code, running as a non-root user. Final
image: 496MB with the full ML stack (down from an initial 3.41GB
before the CUDA-wheel fix).

---

## Testing

**Q: What's actually tested beyond "the endpoint returns 200"?**
A: Mathematical correctness for the similarity engine (controlled
vector tests), gradient-dependence for Grad-CAM (different class →
different heatmap), schema-introspection tests proving the LLM
structurally cannot alter trait scores, cross-user privacy regression
tests, a real Postgres migration-safety cycle against an isolated
database, and a production-like end-to-end flow run against the actual
built Docker images rather than dev servers.

**Q: How do you avoid tests calling real, paid AI APIs?**
A: Every provider-dependent test mocks `get_llm_provider`/
`get_image_generation_provider` directly. No test in the suite calls a
real Anthropic or OpenAI endpoint — confirmed by code review, not
merely assumed.

---

## Architecture

**Q: How would this scale past a single instance?**
A: The two components that are explicitly single-instance today are
documented, not hidden: the in-memory rate limiter (a `RateLimiter`
protocol already exists as the seam for a Redis-backed swap, not built
since it isn't needed yet) and the FAISS index file. Everything else —
stateless FastAPI processes, PostgreSQL, S3-compatible storage — is
already horizontally scalable.

---

## Performance

**Q: What's the measured latency for the interesting endpoints?**
A: From Phase 16/17 measurements on this development machine: FAISS
search ~9ms mean / ~0.3ms median (warm), full similarity endpoint
~524ms mean warm (~9s cold, a one-time `import torch` cost), Grad-CAM
~185–806ms, story generation ~54–572ms. All measured on this specific
machine — never presented as a cross-environment guarantee.

---

## Trade-offs

**Q: What would you improve next?**
A: In priority order: a properly-scoped cat/non-cat detection gate
(the classifier currently has no such gate and will confidently
mis-label a non-cat photo — a real, measured limitation, not
hypothetical); live verification against real Anthropic/OpenAI
credentials and a real S3 bucket (both are implemented and tested
against mocks, never exercised live); a Redis-backed rate limiter, if
and when multi-instance deployment is actually needed; and password
reset/email verification.

**Q: What's a decision you'd defend even though it added complexity?**
A: The three-layer structural separation between real CV signals,
deterministic scores, and LLM-generated text (personality engine).
It would have been simpler to just ask the LLM nicely not to change
the numbers — but a schema with no field for the score is a guarantee,
not a request, and that's worth the extra design work for a product
whose entire credibility rests on being honest about what's real.
