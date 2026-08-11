# MeowVerse AI — Architecture

> Status: Phase 9 complete. Everything through the cinematic reveal +
> collectible Cat Card (Phase 8) is implemented and verified, and
> MeowVerse is now a real multi-user application: email/password
> accounts, DB-backed sessions in httpOnly cookies, server-side
> ownership enforcement on every private resource, a persistent
> per-user collection with favorites/search/filter/sort, real
> statistics, and compute-on-read achievements — all backed by actual
> database queries, never fabricated. Guests can still do everything
> they could before (upload, analyze, view, generate stories); saving
> now requires an account. See §11–§13 for the auth/ownership/storage
> architecture this phase added, and PROJECT_STATUS.md for the current
> phase-by-phase state and real metrics.

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
                         # /login, /register, /profile, /settings, 404
  components/           # shared, presentational UI (shadcn/ui based)
  features/             # feature-scoped UI + logic (upload, analysis,
                         # story, results, collection, auth)
  lib/                  # fetch client, media URL resolver, utils
  hooks/                # shared React hooks (incl. use-auth.ts)
  services/             # typed API client functions (one per resource)
  types/                # shared TS types (mirrors backend Pydantic schemas)
  test-utils/           # shared test helpers (QueryClient-wrapped render)
```

- Styling: Tailwind CSS + shadcn/ui, Framer Motion for motion.
- Data fetching: TanStack Query. `hooks/use-auth.ts` uses it as the
  *actual* client-side auth state store (the `["auth","me"]` query
  result *is* "who's signed in" — no separate Context needed, every
  component reading the hook stays in sync automatically since they
  share the same cache entry). `services/*.ts` are thin `fetch` wrappers
  (`credentials: "include"` on every call so the session cookie flows
  cross-port in local dev) that mutations/queries call into.
- No business logic in components beyond presentation/orchestration.
- Testing (Phase 7): Vitest + React Testing Library, `pnpm test`.
  `vitest.config.ts` uses `pool: "threads"` because the default
  `forks` pool times out spawning worker processes under this Windows
  + OneDrive-synced-path-with-spaces environment. Components using
  TanStack Query render through `test-utils/render-with-query.tsx`
  (fresh `QueryClient` per test, retries off).

## 3. Backend (FastAPI)

```
backend/
  app/
    api/                # routers only: request/response wiring, no logic
      v1/
        auth.py         # register/login/logout/me (Phase 9)
        analyses.py     # analyze/save/favorite/share/unshare
        stories.py      # generate/share/unshare
        collection.py   # /api/v1/me/{collection,stats,achievements} (Phase 9)
        health.py
    core/               # config, security (password/session hashing),
                         # database, rate_limit, auth_deps, csrf, logging
    models/             # SQLAlchemy ORM models (incl. User/Session/
                         # UserAchievement — Phase 9)
    schemas/            # Pydantic request/response schemas
    repositories/       # DB access, one per aggregate (no business rules)
    services/           # business logic, orchestrates repositories + ml/ai
    storage/            # ImageStorageProvider abstraction (Phase 9)
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
  see §14 principle 1.
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

```
users              id, email (unique), password_hash, display_name,
                    avatar_url, created_at, updated_at
sessions            id, user_id → users.id (CASCADE), token_hash
                    (unique — SHA-256 of the cookie's raw token),
                    created_at, expires_at, last_used_at
cat_analyses        id, user_id → users.id (CASCADE, NULLABLE),
                    created_at, updated_at, breed_label,
                    breed_confidence, breed_mode, colors (JSONB),
                    colors_mode, profile (JSONB), profile_mode,
                    cat_name, rarity (denormalized from `profile`),
                    image_url, is_favorite, is_public
stories             id, analysis_id → cat_analyses.id (CASCADE),
                    style, title, story (JSONB), story_mode,
                    provider, model, is_public, created_at
user_achievements   id, user_id → users.id (CASCADE),
                    achievement_key, unlocked_at
                    UNIQUE(user_id, achievement_key)
```

**`cat_analyses`/`stories` were built early, in Phase 7-8**, as a
deliberately minimal subset (`app/models/`, migrations `d64228515183`,
`d64ea3d2f0bd`) — the story and Cat Card features are fundamentally
`analysis_id`-based lookups, which needed *some* real persistence to
exist before Phase 9's auth system did. **Phase 9 extended that same
table** (migration `b04f6df3d75b`) rather than splitting it into the
originally-planned `cat_analyses`/`cat_profiles`/`analysis_results`
three-table design — the single-table shape has been working, tested,
and depended on by every service since Phase 6, and the Phase 9 brief
explicitly says "do not blindly create duplicate tables" / "preserve
existing data where possible." Splitting further is a real option
later if a concrete need for it shows up, not a debt owed today.

Adding `user_id` (nullable — see §12), `cat_name`/`rarity`
(nullable → backfilled from the existing JSONB `profile` column via a
data migration → `NOT NULL`, since 341 real rows already existed in
this dev database when the migration was written and had to keep
their data, not get truncated) required real migration engineering,
not just an `ADD COLUMN`. Verified: upgrade on the actual populated
dev DB, `downgrade` back to the Phase 8 schema, `upgrade` again,
data integrity checked after each step (`count(cat_name) ==
count(rarity) == count(*)`, zero empty-string backfills).

`stories.is_public`/`cat_analyses.is_public` (Phase 7/8) are now
**ownership-gated**: `POST .../share` and the new `POST .../unshare`
both require the caller to own the resource (see §12) — previously
(Phase 7/8, no auth existing yet) these were open to anyone holding
the id. `cat_analyses.is_favorite` (Phase 9) replaces what was a
`localStorage`-only bookmark in Phase 8 with a real, ownership-scoped
column — see §12.

`user_achievements` stores only the unlock *event*; achievement
*definitions* (key, label, emoji, unlock criteria) are static,
code-defined in `app/services/achievement_definitions.py` (same
pattern as `STORY_STYLE_LABELS`), not a second table, since they never
change per-request.

**Deferred, not built this phase**: `generated_assets` (Phase 13 —
nothing to generate yet; the Cat Card's "Generate Wallpaper" button is
still an honest disabled placeholder). Favorites are a column, not a
join table, since a cat has exactly one owner and "favorite" is
inherently owner-scoped — a many-to-many table would model a
relationship that can't occur.

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
  use-cat-actions.ts           # Save/Favorite mutations + optimistic UI (Phase 9)
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
- **Actions**: Save and Favorite are real, ownership-scoped backend
  actions as of Phase 9 (`use-cat-actions.ts`, TanStack `useMutation`
  with optimistic updates + rollback-on-error — see §12) — this
  supersedes Phase 8's `use-saved-cat.ts`, which merged them into one
  local-only bookmark specifically because no collection page existed
  yet to view either against. Now that `/collection` exists, they're
  split back into their own controls, matching the Phase 9 brief.
  Guests get a beautiful auth prompt instead of a silent no-op (see
  §12's guest-experience note). Share (marks the analysis public via
  the API, then tries `navigator.share()` and falls back to a
  clipboard-copy with visible "Link copied!" feedback — now
  ownership-gated too, disabled with a "Save this cat first" tooltip
  until the cat is owned), Download PNG (`html-to-image`, below),
  Generate Story (scrolls to the existing `StorySection`, does not
  duplicate its logic), Generate Wallpaper (disabled, labeled "Coming
  in a future update" — Phase 13 territory, spec explicitly said
  placeholder-only).
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
  read-only card implementation to keep in sync). As of Phase 9 the
  cat photo shown here is real, not a placeholder: `CatCard` falls
  back to the persisted `image_url` (resolved to an absolute backend
  URL via `lib/media.ts`) whenever no local blob-preview URL prop is
  passed, which is every view except the just-analyzed page itself.

## 11. Authentication & Sessions (Phase 9)

**Session strategy: DB-backed opaque tokens in an httpOnly cookie —
not JWT**, despite `jwt_secret`/`jwt_algorithm`/`python-jose` having
been pre-staged in Phase 1's config/dependencies for exactly this
purpose. The decision, and why it overrides that earlier plan:

- **Real logout.** A stateless JWT can't be revoked without a
  server-side blocklist — at which point it's no longer meaningfully
  stateless anyway. A DB row (`sessions`) deleted on logout is an
  immediate, unambiguous "this session no longer works," which the
  spec explicitly asks for ("Implement: ... logout, invalid session
  handling").
- **Same "never store the secret" principle as passwords.** The raw
  token (`secrets.token_urlsafe(32)`, 256 bits of real entropy) only
  ever exists in the client's cookie and in memory for the single
  request that creates/verifies it. The DB stores `sha256(token)` —
  a cryptographic hash, not a slow salted KDF like bcrypt, because the
  token already has full entropy and was never meant to be
  memorable/guessable; hashing it is about limiting the blast radius
  of a DB leak, not defending against brute force.
- **Cookie attributes**: `httponly=True` (unreadable by JS — the spec
  explicitly says avoid `localStorage` for this reason),
  `samesite="lax"` (see CSRF below), `secure=` from
  `settings.session_cookie_secure` (`False` in local dev over plain
  `http://localhost`, meant to be `True` behind HTTPS in production),
  `max_age` from `settings.session_expire_days` (30).
- **Password hashing: `bcrypt` directly, not `passlib[bcrypt]`**
  (also pre-staged in Phase 1). Verified against this project's actual
  installed versions before writing any auth code:
  `passlib==1.7.4` + `bcrypt==5.0.0` throws
  `AttributeError: module 'bcrypt' has no attribute '__about__'` on
  the very first `.hash()` call — passlib's bcrypt backend hasn't been
  updated for bcrypt's 4.x+ API changes and the project is
  unmaintained. `app/core/security.py` calls `bcrypt.hashpw`/
  `bcrypt.checkpw` directly instead: simpler, actively maintained, one
  fewer compatibility shim to break under a future dependency bump.

`app/core/auth_deps.py` provides two FastAPI dependencies:
`get_current_user_optional` (reads the cookie, returns the `User` or
`None` — used by endpoints that serve both guests and signed-in users,
like `POST /api/v1/analyses`) and `get_current_user` (401s if
`get_current_user_optional` returned `None` — used by every genuinely
protected endpoint). Both funnel through
`auth_service.get_user_from_session_token`, so "missing cookie,"
"expired session," and "forged/unknown token" all collapse to the
same `None` → same 401, with nothing more specific to leak.

## 12. Ownership & Privacy Model (Phase 9)

**Every private-resource operation goes through an ownership-scoped
repository function** — `get_owned_analysis`/`get_owned_story`,
`claim_analysis`, `set_favorite`, `set_public`/`set_private` (both
analysis and story versions) all take a `user_id` and filter by it at
the query level. There is no code path that fetches a private resource
by id alone and checks ownership afterward in the route handler — the
*query itself* can't return a row that isn't the caller's, which is
what makes "a user can never access another user's private analysis by
changing an ID" (Phase 9 spec §8) a structural guarantee rather than a
convention that a future endpoint could forget to follow. Not-found
and not-yours both 404 identically, for the same anti-enumeration
reason logins give an identical error for "no such email" and "wrong
password."

**Guest → owner flow**: `POST /api/v1/analyses` takes
`get_current_user_optional` — if the request carries a valid session,
`analysis_service.analyze_image` passes that `user_id` straight
through and the row is auto-owned, no separate save step needed. A
guest's analysis is created with `user_id = NULL`: fully functional
(breed, colors, profile, story generation all still work), just
invisible to any collection query (which always filters
`WHERE user_id = :caller`) until explicitly claimed via
`POST /api/v1/analyses/{id}/save`. That endpoint only succeeds if the
row is *currently* unowned (`claim_analysis` checks `user_id IS NULL`
in the same statement) — so it can't be used to "adopt" someone else's
already-claimed cat by guessing its id. This is also the mechanism
that keeps demo/anonymous browsing from silently becoming a permanent
record (Phase 9 spec §17): nothing is added to anyone's real
collection, stats, or achievements until this explicit act happens,
and stats/achievements queries only ever see `user_id`-owned rows in
the first place.

**Public view sanitization**: `analysis_row_to_result(row, *,
viewer_is_owner: bool)` takes that flag as a required kwarg with no
default — every call site has to state which case it's in. When
`viewer_is_owner=False` (the public `/cat/[id]` path), `owned` and
`is_favorite` are hard-set to `False`/`False` regardless of the row's
actual values — a real bug caught during this phase's own testing: the
first version computed `owned` from `row.user_id is not None` even on
the public path, which would have told a random stranger "yes, someone
owns this" and, worse, leaked the *owner's own* favorite status on
their public share page. Neither field is sensitive in the way an
email address is, but both are "intended-private" per the spec's "public
pages should expose only intended public information," and a
careless frontend could otherwise render a stranger's `owned: true` as
if it meant *their own* device had saved it.

**CSRF**: primary defense is the session cookie's `SameSite=Lax`
attribute — modern browsers don't attach it to cross-site requests
that aren't top-level navigations, which covers the standard
"evil-site.com auto-submits a request to meowverse" case for
essentially all real browsers. `app/core/csrf.py`'s
`verify_same_origin` dependency is defense-in-depth on top of that: it
checks the `Origin` header (sent on virtually all fetch/XHR requests)
against `settings.cors_origins` and 403s on a mismatch, applied to
every state-changing endpoint that acts on the ambient session cookie
(logout, save, favorite/unfavorite, share/unshare, profile update) —
not to login/register, which don't rely on pre-existing auth to do
anything. Deliberately not a double-submit-token scheme: for a
same-origin-by-configuration SPA+API pair with zero cross-site form
posting anywhere in the product, Origin-checking covers the real
threat model without the frontend-side token bookkeeping that scheme
would add.

**Rate limiting** (`app/core/rate_limit.py`) is now behind a
`RateLimiter` protocol — `InMemoryRateLimiter` (fixed 60s window, same
algorithm as Phase 6) is the only implementation, but a Redis-backed
one (sorted set + `ZREMRANGEBYSCORE`/`ZADD`/`ZCARD`, or a Lua token
bucket) is a drop-in replacement for multi-instance deployment without
touching `enforce_rate_limit`/`enforce_auth_rate_limit`'s call sites.
`enforce_auth_rate_limit` uses a tighter limit
(`auth_rate_limit_per_minute`, default 10) and a separate key prefix
(`auth:{ip}`) than the general API limiter, applied to register/login
specifically — brute-forcing passwords is a different threat model
than "don't hammer the AI endpoints."

## 13. Image Storage (Phase 9)

`app/storage/base.py`'s `ImageStorageProvider` ABC (`save`,
`is_available`) is not hard-coded to one backend.
`LocalImageStorageProvider` (disk, under `backend/uploads/`, served
back out via a `StaticFiles` mount at `/media`) is the only
implementation today — real, not a stub, since the collection page
genuinely needs the photo to survive a refresh — but the interface is
shaped so an S3-compatible provider is a later drop-in swap with no
caller changes. Persisting the photo is best-effort, same philosophy
as the analysis row itself: a storage failure never fails the analyze
request, it just means `image_url` stays `None` and the Cat Card falls
back to its placeholder emoji. Storage credentials (whatever a future
cloud backend needs) would live only in backend env vars — the
interface never accepts or returns them, so there's nothing for the
frontend to receive even by accident.

## 14. Key Principles Driving This Architecture

1. Real ML predictions vs AI-generated creative content are always
   labeled and never conflated in the API response shape — including
   using different mode vocabulary (`"trained"` for real CV
   predictions vs `"generated"` for AI-authored creative content) so
   the two can't be accidentally rendered with the same "real" styling
   even by a future engineer who doesn't know this history.
2. Providers (LLM, image-gen, ML models, image storage) are behind
   interfaces so any one of them can be swapped or run in demo/fallback
   mode independently.
3. Business logic lives in `services/`, never in API routes or React
   components.
4. Every private-resource query is ownership-scoped at the query
   level, not checked after the fact in a route handler — see §12.
