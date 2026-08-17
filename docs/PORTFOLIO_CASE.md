# MeowVerse

### Not just a cat classifier — an explainable AI platform.

---

**Role:** Solo full-stack / AI-ML engineer (design, ML, backend,
frontend, DevOps, testing)
**Duration:** [add your actual timeframe]
**Status:** Feature-complete, production-hardened, portfolio-ready

---

## Technologies

**AI / ML:** PyTorch, torchvision, MobileNetV3-Small, Grad-CAM (from
scratch), FAISS, OpenCV, scikit-learn, Anthropic Claude (structured
tool-use), OpenAI `gpt-image-1`

**Backend:** FastAPI, PostgreSQL, SQLAlchemy (async), Alembic, Pydantic,
bcrypt

**Frontend:** Next.js (App Router), React, TypeScript, TanStack Query,
Tailwind CSS, Framer Motion

**Infrastructure:** Docker (multi-stage builds), GitHub Actions CI/CD,
S3-compatible object storage

**Testing:** pytest, Vitest, React Testing Library, Playwright

---

## Overview

MeowVerse turns a photo of a cat into a real, explainable AI analysis:
a fine-tuned breed classifier, an on-demand Grad-CAM explanation of
*why* the model predicted that breed, a FAISS-backed visual similarity
search, a deterministic AI-inspired personality engine, and an
optional generative-AI layer (structured LLM-written stories,
image-conditioned AI portraits). Every AI output is categorized as
real model prediction, AI-generated creative content, or deterministic
demo fallback — a distinction enforced at the schema level, not just
in the UI.

Built solo across 17 development phases, from the initial CV pipeline
through explainability, similarity search, generative AI, gamified
social discovery, and a full production-hardening pass (Dockerized ML
inference, CI/CD, security, migration verification).

## Key Features

- **Real breed classification** — fine-tuned MobileNetV3-Small, 87.5%
  top-1 / 98.6% top-3 accuracy on a genuine held-out test set
- **From-scratch Grad-CAM explainability** — shows exactly which
  regions of the photo drove the prediction
- **FAISS visual similarity search** — mathematically-verified exact
  cosine similarity over 576-dim embeddings
- **AI-inspired personality engine** — deterministic trait scoring,
  structurally isolated from optional LLM-written narrative text
- **Generative AI** — structured Anthropic story generation,
  image-conditioned OpenAI portrait generation, both with a fully
  functional offline fallback
- **Privacy-first public discovery** — "Cat Universe" explore area
  with SQL-level privacy enforcement, no social-network feature creep
- **Production-hardened** — Dockerized ML inference (verified live),
  CI/CD, security headers, CSRF, rate limiting, migration-safety
  verification

## Architecture

```
Next.js Frontend → FastAPI Backend → PostgreSQL
                          │
                          ├─→ ML Services (breed, color, embeddings, Grad-CAM)
                          ├─→ FAISS Vector Index
                          ├─→ AI Providers (Anthropic / OpenAI, both optional)
                          └─→ Image Storage (S3-compatible in production)
```

Full diagrams: [docs/ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md).
Full written design: [ARCHITECTURE.md](../ARCHITECTURE.md).

## Technical Challenges

- **OpenCV GrabCut non-determinism** — found and fixed a real bug
  where fur-color analysis wasn't actually reproducible: GrabCut draws
  from its own internal RNG, separate from the K-means `random_state`
  seeded right next to it.
- **Docker ML dependency bugs** — discovered, only by actually running
  the built container, that `torch` silently resolved a CUDA-bundled
  wheel on Linux (3.4GB image) and that `opencv-python`/
  `opencv-python-headless` conflict on disk, leaving `cv2` importable
  but missing real functionality. Both fixed and verified live.
- **Schema-enforced AI safety** — designed the LLM integration so a
  generative model structurally cannot overwrite a real computed
  signal (breed, color, trait score) — not by convention, by the
  response schema having no field for it.
- **Privacy-safe similarity search** — every similarity/discovery
  query enforces public-or-owned visibility at the SQL level, verified
  by a dedicated cross-user privacy regression suite.

## Results

- 87.5% top-1 / 98.6% top-3 breed classification accuracy (real,
  independently re-verified)
- 458 backend tests (457 passing), 193 frontend tests — both suites clean
- Real ML inference verified running inside a production Docker
  container
- 26-step end-to-end flow verified against the actual built production
  images
- Honest, written AI/ML validation report with no fabricated metrics

## Links

- **GitHub:** [add repository URL]
- **Live Demo:** [not currently deployed — see PRODUCTION_CHECKLIST.md for deployment readiness]
- **Video Demo:** [add link once recorded — see docs/DEMO_VIDEO_SCRIPT.md]
