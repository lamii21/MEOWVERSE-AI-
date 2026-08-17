# MeowVerse — Engineering Case Study

A full-stack AI/ML platform that turns a cat photo into a real
computer-vision analysis, an explainable prediction, a visual
similarity search, and an optional generative-AI creative layer —
built and hardened across 17 phases of iterative engineering.

## 1. Problem

Most "AI cat classifier" portfolio projects stop at a single trained
model behind a form: upload a photo, get a label, done. That doesn't
demonstrate the parts of ML engineering that actually matter in
production — explainability, calibration, privacy-safe similarity
search, honest handling of generative-AI failure modes, or the
operational discipline (Docker, CI, migrations, security) that turns a
notebook into a deployable service. The problem MeowVerse set out to
solve was narrower than "recognize a cat breed" and broader than
"ship a demo": build every layer of a real AI product, and be able to
defend every claim it makes about itself.

## 2. Vision

An AI-powered cat platform where every AI output is honestly
categorized as one of three things — a real model prediction, an
AI-generated creative interpretation, or a deterministic offline
fallback — and where that distinction is enforced *structurally*, not
just in the UI copy. A recruiter or engineer should be able to read
the code and verify the same claims the product makes to a user.

## 3. Product concept

Upload a cat photo → get a real breed prediction and fur-color
analysis → see *why* the model predicted that breed (Grad-CAM) → find
visually similar cats (FAISS) → get an AI-inspired personality (a
deterministic scoring engine plus an optional LLM-written narrative) →
generate a story and an AI portrait → save it to a collection with
gamification (XP, levels, achievements) → optionally share it into a
privacy-first public discovery area, "Cat Universe."

## 4. Architecture

Next.js (App Router, TanStack Query) frontend talking to a FastAPI
backend over a REST API with httpOnly-cookie sessions. PostgreSQL for
all persistent state (users, analyses, stories, personalities,
portraits, embeddings). A FAISS vector index for similarity search.
Image storage behind a swappable `ImageStorageProvider` interface
(local disk for dev, S3-compatible for production). Two independent,
swappable AI provider abstractions (`LLMProvider`,
`ImageGenerationProvider`), each with a `Null*` implementation so the
whole product runs with zero AI API keys configured. See
[ARCHITECTURE.md](../ARCHITECTURE.md) for the full 38-section design
history and [docs/ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)
for diagrams.

## 5. ML pipeline

Image → validation (format, size, min/max dimensions) → breed
classification (MobileNetV3-Small, fine-tuned) → fur color analysis
(GrabCut + K-means) → visual embedding (a *separate*,
non-fine-tuned MobileNetV3-Small, so similarity search isn't just a
breed-label lookup) → FAISS similarity search → on-demand Grad-CAM →
deterministic personality scoring → optional generative layer. See
[docs/ML_PIPELINE.md](ML_PIPELINE.md) for the full breakdown of what's
trained vs. deterministic vs. generated.

## 6. Computer vision

The breed classifier is real transfer learning, not a placeholder: an
ImageNet-pretrained MobileNetV3-Small, fully fine-tuned on the
Oxford-IIIT Pet dataset's 12 cat breeds (2,371 images, 70/15/15
split, seed=42 for reproducibility). Evaluated on a genuine held-out
test set — 87.5% top-1 accuracy, 98.6% top-3 — and re-evaluated
independently during Phase 16's validation pass, producing
byte-identical numbers to the original training run (confirming the
pipeline is actually reproducible, not just claimed to be).

## 7. Explainability

Grad-CAM (Selvaraju et al., 2017) was implemented from scratch with
PyTorch forward/backward hooks against the classifier's real
gradients — not the `pytorch-grad-cam` library that was already a
dependency, and not a decorative or hard-coded heatmap. The target
layer (`features[-1]`, producing a `(576, 7, 7)` feature map) was
verified by inspecting real tensor shapes, not assumed from
architecture documentation. A dedicated test confirms a *different*
target class produces a *different* heatmap — proof the explanation is
actually gradient-dependent, not a static image transform.

## 8. Similarity engine

Every analyzed cat gets a 576-dimensional visual embedding from a
second, separately-loaded MobileNetV3-Small — deliberately the stock
ImageNet-pretrained weights, not the fine-tuned breed classifier, so
"visually similar" reflects how a photo actually looks rather than
just reusing the breed label as a similarity signal. FAISS's
`IndexFlatIP` (exact, not approximate, cosine similarity via inner
product on L2-normalized vectors) backs the search. Mathematical
correctness was verified with controlled vector tests — identical
vectors score 1.0, orthogonal vectors score 0.0, opposite vectors
score negative, and a closer vector always outranks a farther one —
not just "the HTTP endpoint returns 200."

## 9. Generative AI

Two independent provider abstractions, both structurally prevented
from touching real CV output. The Anthropic integration uses **forced
tool use**: the tool's `input_schema` is generated directly from the
Pydantic response model, so the LLM cannot return anything but that
exact shape, and that shape has no fields for breed/color/trait
scores — it *cannot* overwrite real signals because the schema gives
it nowhere to put them. The OpenAI portrait generator uses the cat's
actual uploaded photo as the primary identity reference (image-editing,
not text-only generation), with a backend-only prompt builder that
never lets user-supplied text override identity-preservation rules.
Both providers degrade to a deterministic, clearly-labeled offline
fallback when no key is configured — the entire product is designed
to be, and was tested as, fully functional with zero AI keys.

## 10. Personality engine

A deliberate three-layer separation: Layer A (real CV signals) → Layer
B (8 deterministic trait scores from a documented formula — zero ML,
zero LLM, zero randomness) → Layer C (an optional LLM-written
narrative that can only ever produce flavor text). The separation is
enforced structurally: the `PersonalityInterpretation` schema the LLM
populates has no fields for trait scores or archetype identity,
verified by a dedicated schema-introspection test, so "regenerate the
text" can never silently change "what the numbers say."

## 11. Production engineering

The backend Docker image originally only ever ran in demo mode — a
gap that persisted from Phase 4 until Phase 17, when the image was
rewritten as a proper multi-stage build that actually installs and
runs the ML dependencies. The frontend gained a real production build
target (`output: "standalone"`) instead of only ever having a dev
server. Startup now distinguishes REQUIRED (ML dependencies, when
declared required) from OPTIONAL (nothing today) from DEMO FALLBACK
(the AI providers, deliberately never gated) — and fails loudly instead
of silently degrading when something REQUIRED is missing.

## 12. Security

SQL-level privacy enforcement everywhere (never fetch-then-check),
bcrypt password hashing, DB-backed revocable sessions instead of JWT,
CSRF via `SameSite` + Origin-header defense-in-depth, environment-driven
CORS with a startup-time wildcard refusal in production, a full
security-headers suite (CSP/HSTS/etc.), and per-category rate limiting
on every AI-cost-bearing endpoint. A real decompression-bomb bug was
found and fixed this way — a crafted image that would have caused an
unhandled 500 instead of the same honest 422 every other malformed
upload gets.

## 13. Testing

458 backend tests (457 passing, 1 environment-conditional skip), 193
frontend tests, both suites clean. Beyond count: mathematical
correctness tests for the similarity engine, gradient-dependence tests
for Grad-CAM, schema-introspection tests proving the LLM can't touch
trait scores, a real Postgres migration cycle (fresh upgrade → full
downgrade → re-upgrade) against an isolated database, and a
production-like 26-step end-to-end flow run against the actual built
Docker images — not dev servers.

## 14. Challenges

Real problems hit during development, not invented for narrative
effect:

- **`torch` + `faiss-cpu` OpenMP conflict** (Phase 11) — both bundle
  their own OpenMP runtime; loading both in one process aborted the
  interpreter outright on Windows. Fixed with the standard
  `KMP_DUPLICATE_LIB_OK=TRUE` workaround.
- **`faiss.IndexIDMap` doesn't support `reconstruct()`** (Phase 11) —
  the wrapper originally used couldn't reverse a vector_id back into
  its vector, which the similarity-search response needed. Switched
  to `IndexIDMap2`, which maintains the reverse map.
- **GrabCut non-determinism** (Phase 16) — `KMeans(random_state=42)`
  was seeded, but the GrabCut segmentation step feeding it wasn't:
  OpenCV's GrabCut draws from its own internal RNG, entirely separate
  from scikit-learn's. Five repeated calls on identical input produced
  three different results before `cv2.setRNGSeed(42)` fixed it.
- **A twice-recurring test-fixture pollution bug** (Phase 13, then
  again Phase 16) — a similarity-privacy test used a hardcoded fixture
  color; because content-hash embedding dedup is global and permanent,
  every previous local test run silently left behind another
  perfectly-tied analysis (52 found sharing one vector by direct
  measurement). The first "fix" (picking a *more distinctive*
  hardcoded color) just delayed the same bug. The real fix was a
  fresh, `uuid4`-derived color generated on every run.
- **`torch` silently resolving a CUDA-bundled wheel in Docker**
  (Phase 17) — the project's own documented CPU-only intent held on
  the Windows dev machine but not in a Linux container: a plain
  `pip install torch==2.7.1` pulled ~10 `nvidia-cu12` packages,
  producing a 3.41GB image and a ~10-minute install. Fixed by
  installing from PyTorch's CPU wheel index explicitly (496MB image).
- **`opencv-python` vs. `opencv-python-headless` conflict in Docker**
  (Phase 17) — `grad-cam` transitively installs the GUI-capable
  `opencv-python` alongside the headless build the project actually
  asks for; whichever installs last silently overwrites `cv2` on disk.
  A first fix (uninstalling the GUI build) made it *worse* — `cv2`
  stayed importable but `cv2.cvtColor` no longer existed, since
  uninstall only removes files that package owns, not files it had
  overwritten. The real fix is a forced, dependency-free reinstall of
  the headless build.
- **A decompression-bomb image crashing the analyze endpoint**
  (Phase 17) — Pillow's own `DecompressionBombError` wasn't in the
  endpoint's caught-exception list, so a crafted image with extreme
  declared dimensions produced an unhandled 500 instead of the same
  honest 422 every other malformed upload gets. Found by writing a
  real reproduction, not by code inspection.
- **A `.gitignore` pattern silently excluding new production env
  templates** (Phase 17) — the new `.env.production.example` files
  didn't match the existing `!*.env.example` negation pattern (wrong
  suffix), so `git status` never showed them as addable. Found by
  checking `git status` after writing them, not assumed to work.

## 15. Engineering decisions

- **DB-backed opaque sessions over JWT** — a leaked or compromised
  session can be revoked immediately server-side; a JWT can't be
  invalidated before its expiry without an extra revocation-list
  system, which would have been more complexity for less security.
- **A generic ImageNet embedding model for similarity, not the
  fine-tuned breed classifier** — using the breed classifier's own
  features would make "similar cats" collapse into "same predicted
  breed," which isn't what visual similarity should mean.
- **Structural (schema-level) separation of AI-generated text from
  computed signals**, everywhere an LLM touches the product — a
  convention ("the LLM shouldn't change the score") is a promise; a
  schema with no field for the score is a guarantee.
- **In-memory rate limiting kept, Redis-backed limiter not built** —
  the `RateLimiter` protocol exists specifically as a drop-in seam for
  this, but building an unused Redis-backed implementation for a
  single-instance deployment would have been complexity with no
  present payoff.
- **Committing the trained model weights directly to the repository**
  (~6MB) rather than object storage or a release-asset download step —
  the safest option at this size: no runtime download, no extra
  infrastructure, and the exact weights the validation report measured
  are guaranteed to be the ones deployed.

## 16. Limitations

Stated plainly: no cat/non-cat detection gate (the classifier will
confidently mis-label a dog); live Anthropic/OpenAI calls not verified
in this development environment (no keys configured); the in-memory
rate limiter doesn't scale across multiple instances; real S3
credentials never exercised; no password reset flow; and a measured
4.4% high-confidence-wrong rate on the test set. Full detail in
[AI_VALIDATION_REPORT.md](../AI_VALIDATION_REPORT.md) and the
README's Known Limitations section.

## 17. Results

87.5% top-1 / 98.6% top-3 breed classification accuracy on a genuine
held-out test set. 458 backend tests (457 passing), 193 frontend
tests, all clean. Real inference verified running inside a production
Docker container. A 26-step end-to-end flow verified against the
actual built production images. Three real Docker-specific bugs found
and fixed only by actually running the built image, not by trusting
`docker build`'s exit code.

## 18. Future improvements

A properly-scoped cat/non-cat detection gate. Live verification against
real Anthropic/OpenAI credentials and a real S3 bucket. A Redis-backed
rate limiter, if and when multi-instance deployment is actually
needed. Password reset / email verification. A formal similarity
retrieval benchmark, if a labeled "these two photos are the same cat"
ground-truth dataset ever becomes available.
