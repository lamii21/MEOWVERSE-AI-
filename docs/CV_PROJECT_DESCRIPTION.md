# MeowVerse — CV / Résumé Descriptions

Four versions, from a single line to a full technical-interview
answer. Every claim below is grounded in the actual repository — see
[AI_VALIDATION_REPORT.md](../AI_VALIDATION_REPORT.md) and
[PROJECT_STATUS.md](../PROJECT_STATUS.md) for the underlying evidence.

---

## Version A — One line

> **MeowVerse** — an explainable AI platform combining fine-tuned computer vision, FAISS-backed visual similarity search, from-scratch Grad-CAM, and structured generative AI, deployed as a production-hardened full-stack application (Next.js, FastAPI, PostgreSQL, Docker).

---

## Version B — Two bullet points

- Built **MeowVerse**, a full-stack AI platform (Next.js/FastAPI/PostgreSQL) that fine-tunes a CNN for cat breed classification (87.5% top-1 accuracy on a held-out test set), implements Grad-CAM explainability from scratch, and runs a FAISS-backed visual similarity search over 576-dim embeddings — with mathematically-verified correctness, not just passing HTTP tests.
- Engineered a structured generative-AI layer (Anthropic forced tool-use, OpenAI image-conditioned generation) with schema-enforced guarantees that LLM output can never overwrite real model predictions, plus a fully-functional deterministic fallback path when no AI provider is configured — then hardened the whole system for production: Dockerized ML inference, CI/CD, security headers, and a real migration-safety verification pass.

---

## Version C — Three bullet points

- **Computer vision & explainability**: fine-tuned MobileNetV3-Small (transfer learning) on the Oxford-IIIT Pet dataset for 12-class cat breed classification (87.5% top-1 / 98.6% top-3 on a genuine held-out test set), plus a from-scratch Grad-CAM implementation (PyTorch hooks against real gradients, not a wrapper library) verified with gradient-dependence tests.
- **Similarity search & generative AI**: a separate ImageNet-pretrained embedding model feeding an exact-cosine-similarity FAISS index (mathematically verified, not just HTTP-tested), alongside a structured LLM integration (Anthropic forced tool-use) and image-conditioned generation (OpenAI `gpt-image-1`) — both schema-guaranteed to never overwrite real CV output, both with a fully-functional deterministic offline fallback.
- **Production engineering**: Dockerized the real ML pipeline (previously demo-mode-only in containers — fixed and verified via live inference inside the running container), added CI/CD with a Docker build gate, security headers, CSRF/CORS hardening, and verified a full Postgres migration cycle (upgrade → downgrade → re-upgrade) against an isolated database. 458 backend tests, 193 frontend tests, both suites clean.

---

## Version D — Detailed technical-interview version

**MeowVerse** is a full-stack AI/ML platform I built end-to-end across
17 development phases: a Next.js frontend, a FastAPI backend, and
PostgreSQL for persistence, with Docker/CI-CD for deployment.

The core computer-vision pipeline fine-tunes an ImageNet-pretrained
MobileNetV3-Small on the Oxford-IIIT Pet dataset (12 cat breeds, 2,371
images, a 70/15/15 split with a fixed seed for reproducibility),
reaching 87.5% top-1 / 98.6% top-3 accuracy on a genuine held-out test
set — a number I independently re-derived in a later validation pass
and confirmed byte-identical to the original training run. Fur color
is analyzed via OpenCV GrabCut segmentation feeding scikit-learn
K-means, which I found and fixed a real non-determinism bug in: GrabCut
draws from OpenCV's own internal RNG, separate from scikit-learn's
`random_state`, so the pipeline wasn't actually deterministic until I
seeded it explicitly.

For explainability, I implemented Grad-CAM from scratch with PyTorch
forward/backward hooks against the classifier's real gradients —
deliberately not using the `pytorch-grad-cam` library that was already
a dependency, so every step stays auditable and testable. I verified
the target layer empirically (inspecting real tensor shapes rather
than assuming from architecture docs) and wrote a test confirming a
different target class produces a genuinely different heatmap.

For visual similarity, I built a separate embedding pipeline — a
second, non-fine-tuned MobileNetV3-Small — specifically so "similar
cats" reflects how a photo actually looks rather than collapsing into
"same predicted breed." FAISS's `IndexFlatIP` gives exact (not
approximate) cosine similarity, and I wrote controlled mathematical
tests (identical/orthogonal/opposite/ranked vectors) to verify the
similarity math itself, not just that the HTTP endpoint returns 200.

On the generative-AI side, I integrated Anthropic's Claude using
forced tool-use — the tool's `input_schema` is generated directly from
the Pydantic response model, so the LLM structurally cannot return
anything but that exact shape, and that shape has no fields for
breed/color/trait scores, so it can't overwrite real model output even
if it tried. For AI portrait generation, I use OpenAI's `gpt-image-1`
in image-editing mode, attaching the cat's actual photo as the primary
identity reference rather than describing it in text. Both providers
fall back to a deterministic, clearly-labeled offline mode when no key
is configured, and I explicitly tested that the entire product remains
fully functional with zero AI API keys — nothing crashes, nothing is
silently faked as real.

For production readiness, I found that the backend's Docker image had
been running the CV pipeline in demo mode since early development — a
gap I closed by rebuilding it as a proper multi-stage image that
installs the real ML dependencies, then verified live (not just via a
successful build) that a real photo uploaded to the running container
returns a correct trained prediction with a working Grad-CAM heatmap.
Along the way I found and fixed two genuinely tricky Docker-specific
bugs: `torch` silently resolving PyPI's CUDA-bundled wheel on Linux
despite the project's own CPU-only intent (fixed via PyTorch's CPU
wheel index, cutting the image from 3.4GB to 496MB), and a package
conflict between `opencv-python` and `opencv-python-headless` that
left `cv2` importable but missing real functionality — where my first
fix attempt (uninstalling the conflicting package) made things worse,
teaching me that `pip uninstall` doesn't restore files a package
overwrote, only removes the ones it owns.

The system currently has 458 backend tests (457 passing, one
environment-conditional skip) and 193 frontend tests, both suites
clean, plus a real Postgres migration-safety verification (a full
upgrade → downgrade → re-upgrade cycle against an isolated database)
and a 26-step end-to-end flow run against the actual built production
Docker images. I'm equally comfortable stating what's *not* verified:
live Anthropic/OpenAI calls haven't been tested in this environment
(no API keys configured), there's no cat/non-cat detection gate (a
real, measured limitation — a dog photo was classified as "Abyssinian"
at 94.5% confidence), and the rate limiter is in-memory and won't
scale past a single instance without a documented (but not yet built)
Redis-backed swap.
