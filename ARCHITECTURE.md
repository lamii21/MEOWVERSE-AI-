# MeowVerse AI — Architecture

> Status: Phase 8 complete. Frontend scaffold, landing page, upload/
> analysis workflow, the real breed classifier (transfer learning,
> 87.5% test accuracy), real fur-color extraction (GrabCut + K-means),
> real AI profile generation, real AI story generation (Anthropic,
> forced tool-use), and now the cinematic reveal + collectible Cat Card
> experience are implemented and verified end-to-end — breed/colors/
> profile/story can each independently be real or demo. Phase 7 added a
> minimal real Postgres persistence layer (`cat_analyses`, `stories`
> tables) ahead of Phase 9's full schema; Phase 8 extended it with
> `is_public` sharing for analyses too — see §6 for why. See
> PROJECT_STATUS.md for the current phase-by-phase state and real
> metrics; this document describes the target architecture, with notes
> on what's implemented vs. still planned.

## 1. System Overview

MeowVerse AI turns a photo of a cat into a generated "cat profile": a real
computer-vision breed/color analysis, plus clearly-labeled AI-generated
creative content (personality, story, magic power, rarity).

```
┌──────────────┐      REST/JSON      ┌───────────────┐
│   Frontend    │ ◄─────────────────► │    Backend     │
│  Next.js/TS   │                     │   FastAPI      │
└──────────────┘                     └───────┬────────┘
                                              │
                        ┌─────────────────────┼─────────────────────┐
                        ▼                     ▼                     ▼
                ┌───────────────┐   ┌──────────────────┐   ┌────────────────┐
                │  PostgreSQL   │   │   ML Pipeline      │   │  Redis (cache/  │
                │  (users,      │   │  (detection,       │   │  background     │
                │   analyses,   │   │   breed, color,    │   │  jobs)          │
                │   profiles)   │   │   embeddings,      │   │                 │
                └───────────────┘   │   Grad-CAM)        │   └────────────────┘
                                    └─────────┬──────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │ Generative Providers │
                                    │ LLMProvider (text)    │
                                    │ ImageGenProvider (img) │
                                    │ pluggable / swappable  │
                                    └───────────────────────┘
```

## 2. Frontend (Next.js + TypeScript)

```
frontend/
  app/                  # routes: /, /discover, /analyze, /cat/[id],
                         # /story/[id], /collection, /collection/[id],
                         # /dashboard, /login, /register, /profile,
                         # /settings, /achievements, 404
  components/           # shared, presentational UI (shadcn/ui based)
  features/             # feature-scoped UI + logic (upload, analysis,
                         # story, results, collection, achievements, auth)
  lib/                  # fetch client, query client config, utils
  hooks/                # shared React hooks
  services/             # typed API client functions (one per resource)
  types/                # shared TS types (mirrors backend Pydantic schemas)
```

- Styling: Tailwind CSS + shadcn/ui, Framer Motion for motion.
- Data fetching: TanStack Query, thin `services/` layer wraps `fetch`
  (story generation currently uses plain `fetch` in `services/stories.ts`,
  matching `services/analyses.ts` — not yet migrated to TanStack Query).
- No business logic in components beyond presentation/orchestration.
- Testing (Phase 7): Vitest + React Testing Library, `pnpm test`. Not
  configured before Phase 7 — this project had zero frontend test
  tooling through Phase 6; `vitest.config.ts` uses `pool: "threads"`
  because the default `forks` pool times out spawning worker processes
  under this Windows + OneDrive-synced-path-with-spaces environment.

## 3. Backend (FastAPI)

```
backend/
  app/
    api/                # routers only: request/response wiring, no logic
      v1/
        auth.py
        analyses.py
        cats.py
        achievements.py
        health.py
    core/               # config, security, logging, settings
    models/             # SQLAlchemy ORM models
    schemas/            # Pydantic request/response schemas
    repositories/       # DB access, one per aggregate (no business rules)
    services/           # business logic, orchestrates repositories + ml/ai
    ml/                 # computer vision pipeline (see below)
    ai/                 # LLMProvider / ImageGenerationProvider abstractions
    workers/            # background jobs (Redis-backed queue)
    utils/              # generic helpers
  alembic/              # migrations
  tests/
```

Layering rule: `api` → `services` → `repositories`/`ml`/`ai`. Routers never
touch the DB or models directly; services never import FastAPI types.

## 4. Computer Vision Pipeline (`backend/app/ml` + `backend/ml`)

```
image
  → validation (format, size, min dimensions)            [implemented]
  → breed classification  (BreedClassifier : BaseModel)   [implemented — Phase 4]
  → fur color analysis    (FurColorAnalyzer : BaseModel)  [implemented — Phase 5]
  → embedding generation  (EmbeddingModel : BaseModel)    [planned — Phase 11]
  → Grad-CAM heatmap      (explainability)                [planned — Phase 12]
  → result aggregation → structured AnalysisResult (Pydantic)
```

Fur color: OpenCV GrabCut foreground segmentation (excludes background
before clustering, falls back to the whole image if the mask ends up
degenerate) → scikit-learn K-means (k=3, fixed seed for determinism)
→ each cluster centroid named via nearest-neighbor lookup against a
small fur-relevant reference palette. Documented in
`app/ml/fur_color.py` as an approximation (RGB nearest-neighbor, not a
perceptually-calibrated color-science technique) — good enough for a
playful palette display, not presented as more rigorous than it is.

There is no separate "cat detection" step: the classifier itself is
cat-only (trained exclusively on cat breeds), so an image of a dog or
non-cat currently gets a (low-confidence, meaningless) breed label
rather than a `detected: false`. A dedicated detection/rejection step
is deferred until it's needed for a specific product requirement.

Two directories, two different jobs:

- **`backend/app/ml/`** — inference-time code loaded by the running
  API: `base_model.py` (the `BaseModel` contract), `breed_classifier.py`
  (`BreedClassifier`, needs trained weights on disk), and
  `fur_color.py` (`FurColorAnalyzer`, no weights — just needs
  opencv/numpy/scikit-learn importable). Both are loaded lazily as
  process-wide singletons via their `get_*()` functions.
- **`backend/ml/`** — offline training pipeline, run manually, never
  imported by the API: `scripts/prepare_dataset.py` (download +
  split), `training/train_breed_classifier.py` (transfer learning),
  `evaluation/evaluate.py` (metrics on the held-out test set),
  `models/` (weights + `class_names.json` + `model_card.json`,
  gitignored except the JSON metadata — see `backend/ml/README.md`).

Key properties actually implemented (Phases 4–5):

- `BaseModel` interface: every model implements `load()`,
  `predict(image) -> result`, exposes `name`, `version`, and
  `is_available`. For `BreedClassifier` that's `False` when trained
  weights (or `torch` itself) aren't present; for `FurColorAnalyzer`
  there are no weights at all, so it's `False` only when
  opencv/numpy/scikit-learn aren't importable. Either way: gate a
  fallback, never raise from `is_available` itself.
- Each signal in `AnalysisResult` carries its **own** mode
  (`breed_mode`, `colors_mode`: `"demo" | "trained"`) instead of one
  result-wide flag — necessary because signals go real independently
  across phases (breed in Phase 4, fur color in Phase 5, ...); a
  single flag would let a still-demo fur palette ride along on a
  `"trained"` label.
- If `BreedClassifier.is_available` is `False` (weights not trained
  yet, or `torch`/`torchvision` not installed at all),
  `analysis_service.py` falls back to a deterministic demo pool
  instead of failing — never silently faked as a real prediction.
- Raw model internals (logits, tensors) never cross the API boundary —
  only structured, validated Pydantic results.

## 5. Generative AI Abstraction (`backend/app/ai`)

```python
class LLMProvider(ABC):
    async def generate_profile(self, signals: CatSignals) -> CatProfile: ...
    async def generate_story(
        self, signals: CatSignals, profile: CatProfile, style: StoryStyle
    ) -> CatStory: ...  # Phase 7 — back on the ABC with a real schema

class ImageGenerationProvider(ABC):  # Phase 13, still a null stub
    async def generate_wallpaper(self, profile: CatProfile) -> dict: ...
    async def generate_avatar(self, profile: CatProfile) -> dict: ...
```

**Implemented (Phase 6 profiles, Phase 7 stories):** `AnthropicLLMProvider`
(`app/ai/anthropic_provider.py`) calls the real `anthropic` SDK using
**forced tool use** — the tool's `input_schema` is generated directly
from `CatProfile.model_json_schema()` / `CatStory.model_json_schema()`,
so the model's response either matches that schema or the call is
treated as invalid and retried once (missing tool call or failed
Pydantic validation), never trusted as-is. Both code paths share one
generic `_call_tool(system, user_prompt, tool, response_model)` helper
rather than duplicating the retry loop. Transport failures (timeout/
connection/status errors) are not retried at this layer and raise
`LLMProviderError` immediately so the caller can fall back quickly
rather than stacking retries on retries.

### Story generation (Phase 7)

- `CatStory` (`app/schemas/story.py`): `title`, `subtitle`, `opening`,
  3–5 `chapters` (each with `chapter_number`/`title`/`text`), `ending`,
  `moral`, `quote` — all length-bounded (`Field(max_length=...)`) so a
  runaway generation can't produce an unbounded wall of text. Five
  `StoryStyle` values (`magical_adventure`, `cozy_wholesome`,
  `funny_chaotic`, `dreamy_emotional`, `fantasy_quest`), each with an
  emoji/title/description pair shared between backend
  (`STORY_STYLE_LABELS`) and frontend (`STORY_STYLE_OPTIONS`).
- `app/ai/story_prompt.py`: a composable, independently unit-tested
  prompt builder — `build_system_prompt()` (rules + safety), per-style
  tone instructions, and `build_cat_context()` which explicitly labels
  which signals are real CV output vs. fictional/creative, so the model
  is never invited to treat its own invented details as fact.
- `app/services/story_service.py` (`get_or_generate_story`): looks up
  the analysis by id (404 via `AnalysisNotFoundError` if missing, never
  a 500), returns the existing story for `(analysis_id, style)` unless
  `regenerate=true` is explicitly passed — **no silent
  auto-regeneration**, matching the same on-demand-generation
  discipline as profiles. Falls back to `story_templates.py`'s
  deterministic demo generator (SHA-256 of the analysis id + style,
  with a `variant_offset` derived from the existing story count so
  clicking Regenerate visibly cycles template variants even without a
  live provider).
- `story_mode` (`"demo" | "generated"`) reuses the same deliberately
  non-"prediction" vocabulary as `profile_mode` — a story is creative
  content, never a prediction, regardless of source.
- Limits: `MAX_STORY_PROMPT_CHARS` (3000, same defensive-ceiling
  pattern as the profile prompt), same `ANTHROPIC_MAX_OUTPUT_TOKENS`/
  `ANTHROPIC_TIMEOUT_SECONDS`/rate-limiter as profile generation — the
  story endpoint (`POST /api/v1/analyses/{id}/story`) is rate-limited
  for the same reason (it can trigger a paid external call), and won't
  call the provider at all if a non-regenerate request already has a
  saved story.

- Concrete providers live behind `LLMProvider`/`ImageGenerationProvider`;
  selected via `.env` config (`LLM_PROVIDER`, `ANTHROPIC_API_KEY`,
  `ANTHROPIC_MODEL`), never hard-coded call sites.
- **`CatProfile` has no breed/color/confidence fields** — this is a
  structural guarantee, not a prompt instruction: the LLM has nowhere
  to put a "real" prediction even if it tried. `app/services/
  profile_service.py` builds `CatSignals` from the real CV results and
  is the only thing that ever constructs the final `AnalysisResult`,
  combining real fields with the separately-validated `CatProfile`.
- If no provider is configured (or the real call fails after retrying),
  `profile_service.py` falls back to one of five hand-written demo
  profiles, selected deterministically from the image bytes — same
  pattern as the CV demo fallbacks — and marks `profile_mode: "demo"`.
  This must never raise and never block the analysis endpoint.
- `profile_mode` (`"demo" | "generated"`) deliberately uses different
  vocabulary than `breed_mode`/`colors_mode` (`"demo" | "trained"`) —
  see §10 principle 1.
- Limits actually enforced: `ANTHROPIC_MAX_OUTPUT_TOKENS` (default
  1024), `ANTHROPIC_TIMEOUT_SECONDS` (default 20s), a 2000-char prompt
  ceiling (defensive — inputs come only from our own bounded CV output),
  and a per-IP rate limiter (`app/core/rate_limit.py`,
  `RATE_LIMIT_PER_MINUTE`, default 20) applied specifically to `POST
  /api/v1/analyses` since it's the only endpoint that can trigger a
  paid external call.
- Security: the API key is env-var only, never touches the frontend
  (only the backend process calls Anthropic), and the `anthropic`/
  `httpx`/`httpcore` loggers are pinned to `WARNING` so request/auth
  data can't leak into logs regardless of the app's own debug level.

## 6. Data Model (high level)

Target (Phase 9): `users`, `cat_analyses`, `cat_profiles`,
`analysis_results`, `stories`, `generated_assets`, `favorites`,
`achievements` — UUID PKs, timestamps, FKs, indexes, full auth.

**Implemented early, in Phase 7, as a deliberately minimal subset:**
`cat_analyses` and `stories` (SQLAlchemy models in `app/models/`,
Alembic migration `d64228515183`). The story feature is fundamentally
`analysis_id`-based lookup (`POST /api/v1/analyses/{id}/story`, `GET
/api/v1/stories/{id}`), which requires *some* real persistence to
exist — building the full Phase 9 schema (auth, users, favorites,
achievements) just to get there would have been scope creep in the
other direction. `cat_analyses` has no `user_id` yet (no auth exists);
`stories.analysis_id` is a `CASCADE`-deleting FK. Analysis persistence
in `analysis_service.py` is deliberately **best-effort**:
`AnalysisResult.id` is `uuid.UUID | None`, `None` if the DB write
fails, and the core `/api/v1/analyses` endpoint still returns 200 with
full breed/color/profile data either way — only the new story
endpoints genuinely require the DB (404 if the analysis wasn't
persisted). `stories.is_public` (default `False`) backs the
`/story/[id]` share page: `POST /api/v1/stories/{id}/share` flips it
public; sharing is always an explicit, one-directional user act, never
automatic.

**Phase 8** added the identical `is_public` column + share endpoint to
`cat_analyses` (migration `d64ea3d2f0bd`), so the Cat Card gets its own
`/cat/[id]` share page independent of whether its story has been
shared — `GET /api/v1/analyses/{id}` (404 unless public) and `POST
/api/v1/analyses/{id}/share`, mirroring the story endpoints exactly.
Neither share endpoint checks ownership — there is still no auth
system (Phase 9) to check against — but the action is additive and
idempotent (it can only ever reveal content the caller already
received in the private response, never mutate or delete anything).

## 7. Similarity Search

- MVP: FAISS index built locally over stored embeddings.
- Interface designed so the vector store can migrate to Postgres
  `pgvector` later without changing the service-layer API.

## 8. Infrastructure

- `docker-compose.yml`: frontend, backend, postgres, redis — local dev
  requires no cloud services.
- GitHub Actions: lint + test + build on push/PR.
- `.env.example` documents all required variables; no secrets in git.

## 9. Cat Card & Reveal Experience (`frontend/features/results`, Phase 8)

Phase 8 replaced the Phase 3–7 placeholder result list (a plain
top-to-bottom summary) with a cinematic reveal and a real collectible
Cat Card, without touching the underlying analysis/profile/story
pipeline that produces the data it displays.

```
features/results/
  rarity.ts                    # Rarity → visual treatment config
  use-card-tilt.ts             # Pointer-driven 3D tilt (CSS transforms via Framer Motion)
  use-saved-cat.ts             # Local "Save" bookmark (useSyncExternalStore)
  components/
    ResultReveal.tsx           # Timed intro beat → render-prop reveal of the rest
    CatCard.tsx                # The collectible card itself + its actions
    RarityAura.tsx             # Per-tier animated flourish (shimmer/glow/aura/particles)
    ConfidenceMeter.tsx        # "Model confidence" meter + explanation
    ColorPalette.tsx           # Designer-style swatch list
    ResultExperience.tsx       # Top-level composition used by /analyze
    PublicCatView.tsx          # Read-only wrapper used by /cat/[id]
```

- **Reveal sequence**: `ResultReveal` shows a timed intro ("A new cat
  has appeared...", ~1.4s) then hands control to a render-prop
  (`children(interactive: boolean)`) so the caller can lay out the Cat
  Card and surrounding content however it needs (e.g. `ResultExperience`'s
  two-column desktop grid) while still knowing whether the reveal has
  settled. The Cat Card's own internal stagger (rarity → image → name →
  breed → magic power → confidence → palette, via the same Framer
  Motion `staggerChildren` pattern `StoryCard` established in Phase 7)
  covers the individual field-reveal beats. `interactive` only flips
  true after the card has visually settled, so pointer-tilt doesn't
  fight the entrance animation. `prefers-reduced-motion` skips straight
  to the finished, fully interactive state — resolved via
  `useReducedMotion()` inside a `useEffect` (not read in a `useState`
  initializer, which would race the hook's own SSR-safe internal
  effect and silently ignore the real preference on first render; a
  real bug caught during this phase's testing, not hypothetical).
- **Rarity visual system** (`rarity.ts` + `RarityAura.tsx`): six tiers
  (Common → Mythical), each a strict superset of polish over the last —
  Common is a plain matte card; Mythical adds a soft particle glow.
  Deliberately restrained per the product brief ("subtle and premium,"
  not flashy): only Rare and up get any motion, and every animated
  variant (shimmer sweep, gradient glow, pulsing aura, twinkling
  sparkles) has a static equivalent under reduced motion rather than
  just switching off.
- **Card interaction**: `use-card-tilt.ts` computes `rotateX`/`rotateY`
  from pointer position via Framer Motion springs — no WebGL, per the
  phase brief. Disabled on touch pointers (mobile gets a tap
  `whileTap` scale instead) and under reduced motion.
- **Actions**: Save (→ `use-saved-cat.ts`, a `localStorage` bookmark
  list keyed by analysis id, same `useSyncExternalStore` pattern as
  Phase 7's story-favorite hook — chosen specifically because
  `useState`+`useEffect` renders the wrong value on the server for any
  component that can appear in an SSR'd tree, which `CatCard` does on
  `/cat/[id]`), Share (marks the analysis public via the API, then
  tries `navigator.share()` and falls back to a clipboard-copy with
  visible "Link copied!" feedback), Download PNG (`html-to-image`,
  below), Generate Story (scrolls to the existing `StorySection`, does
  not duplicate its logic), Generate Wallpaper (disabled, labeled
  "Coming in a future update" — Phase 13 territory, spec explicitly
  said placeholder-only). The brief listed Save and Favorite as
  separate actions; with no collection page to view either against yet
  (Phase 10), two divergent local-only flags would have been dead-end
  UI, so they were deliberately consolidated into the one Save button.
- **PNG export**: `html-to-image`'s `toPng()` snapshots a ref'd DOM
  node (the card's visual content only — the action-button row sits
  outside that ref so it never ends up in the exported image). Real
  gotchas hit and fixed during this phase, not just handled in the
  abstract:
  - `cacheBust: true` (a common `html-to-image` option, initially
    included) appends `?<timestamp>` to every `<img>` src to force a
    fresh fetch — but the cat photo's src is a `blob:` URL, and blob
    URLs don't support query strings at all; appending one produced an
    unresolvable URL and the export threw on every attempt. Removed —
    unnecessary anyway for a one-shot export of a freshly rendered
    node.
  - Export failures surface as an inline "Download failed" button
    state (auto-clears after 3s) rather than silently producing a
    blank file; the code explicitly checks for `toPng`'s empty-export
    sentinel (`"data:,"`) as well as thrown errors.
  - Fonts: self-hosted via `next/font` (Geist Sans/Mono, Quicksand),
    not a remote Google Fonts stylesheet — so `html-to-image` never
    needs to cross an origin to inline them, sidestepping the CORS
    class of font-embedding failures entirely.
- **Sharing**: `/cat/[id]` (`app/cat/[id]/page.tsx`) is a Next.js
  Server Component, same shape as Phase 7's `/story/[id]` — fetches via
  `fetchPublicAnalysis`, calls `notFound()` on a 404 (private or
  missing), otherwise renders `PublicCatView` (a thin read-only wrapper
  around the same `CatCard` used everywhere else — no separate
  read-only card implementation to keep in sync).

## 10. Key Principles Driving This Architecture

1. Real ML predictions vs AI-generated creative content are always
   labeled and never conflated in the API response shape — including
   using different mode vocabulary (`"trained"` for real CV
   predictions vs `"generated"` for AI-authored creative content) so
   the two can't be accidentally rendered with the same "real" styling
   even by a future engineer who doesn't know this history.
2. Providers (LLM, image-gen, ML models) are behind interfaces so any one
   of them can be swapped or run in demo/fallback mode independently.
3. Business logic lives in `services/`, never in API routes or React
   components.
