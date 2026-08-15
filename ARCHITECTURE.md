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

## 15. Gamification & Progression (Phase 10)

**XP is awarded exclusively server-side, keyed by real events, never
trusted from the client** — the frontend never sends an XP value, only
triggers actions (save, favorite, share, generate story) whose
handlers call `app/services/gamification.py`'s `process_event`.

**Anti-farming via an idempotent event log.** `collection_events`
(`app/models/collection_event.py`) has a unique constraint on
`(user_id, event_type, target_id)`. `process_event` inserts with
`ON CONFLICT DO NOTHING` and only awards XP when the insert actually
happened — so the same real-world moment can only ever pay out once,
no matter how many times the underlying action repeats client-side:

- **`CAT_FAVORITED`** is keyed on the analysis id — toggling
  favorite/unfavorite/favorite again pays out exactly once, the first
  time.
- **`STORY_GENERATED`** is keyed on the *analysis* id, not the story
  id — generating a story for a cat pays out once; clicking
  Regenerate (which inserts a brand-new `StoryModel` row each time,
  see `story_repository.save_story`) or picking a different style for
  the same cat never pays out again. Without this, Regenerate would be
  an infinite XP faucet.
- **`CAT_DISCOVERED`** fires once per analysis, from whichever path
  first gives it an owner — an authenticated `POST /api/v1/analyses`
  (auto-owned) or a later `POST .../save` (claimed from a guest
  upload). Same event either way; see §12's guest → owner flow.
- **`CAT_SHARED`** is keyed on the analysis id, fired from
  `POST /api/v1/analyses/{id}/share`; unsharing and re-sharing doesn't
  re-pay.
- **`ACHIEVEMENT_UNLOCKED`** is keyed on the achievement key, fired
  from inside `process_event` itself the moment an achievement newly
  qualifies (see §16) — so unlocking never needs a separate XP grant
  call, and (being append-only-unique same as every other event type)
  can never double-pay even under a race.

**XP values and the level curve** live in
`app/services/progression.py`, the single source of truth both the
API and this document describe from:

| Event | XP |
|---|---|
| Cat discovered | 100 |
| Cat favorited (first time) | 10 |
| Story generated (first time per cat) | 25 |
| Cat shared (first time) | 15 |
| Achievement unlocked | 50 |

**Level formula**: level *N* requires `100 × (N-1)²` cumulative XP
(level 1 = 0, level 2 = 100, level 3 = 400, level 4 = 900, ...),
capped at `MAX_LEVEL = 20` so the number stays a small, legible
milestone rather than growing without bound. Level is *derived* from
`user_progress.xp` on every read (`level_for_xp`), never stored
redundantly — the two can't drift apart because there's only one of
them. Five cosmetic level-title bands (`"Meow Explorer"` →
`"MeowVerse Legend"`) are pure flavor text with no other meaning,
matching the codebase's existing "rarity is a game mechanic, not a
measurement" stance on badges/tags.

**Response shape**: any mutation that itself triggers a gamification
event (`AnalysisResult.gamification` / `StoryResponse.gamification`)
carries a `GamificationEvent` — `xp_awarded` (0 if this was a repeat,
not a new event), `total_xp`, `level`, `leveled_up`, `is_new_breed`,
`is_new_rarity`, and any `newly_unlocked` achievements from *this*
call. A plain `GET` never carries one — viewing something isn't an
event. The frontend's `lib/discovery-toast-store.ts` decomposes this
into a queue of one-at-a-time toasts (breed → rarity → each
achievement → level-up), so a single Save click that happens to hit
several milestones at once doesn't show them all stacked simultaneously.

## 16. Achievement Engine (Phase 10)

Same compute-on-read pattern as Phase 9's original five achievements,
extended to nine: `app/services/achievement_definitions.py` holds
`AchievementDefinition`s (key, emoji, label, description, an
`is_unlocked(stats) -> bool` predicate, and a `progress(stats) ->
(current, target)` pair for the UI's progress bars) — pure functions
over a `stats` dict, no side effects, independently testable.
`collection_service.sync_and_list_achievements` builds that `stats`
dict from real aggregate queries (never demo/fabricated data, since
unowned guest rows can't reach a `user_id`-scoped query in the first
place), checks it against every definition, and unlocks
(`achievement_repository.unlock`, itself `ON CONFLICT DO NOTHING` on
`(user_id, achievement_key)`) any that newly qualify. This runs on
every `process_event` call and every direct `/me/achievements` fetch —
cheap enough (a handful of indexed aggregate queries) to not need a
background job at this scale.

Two Phase 9 keys were *relabeled*, not renamed at the DB level
(`legendary_hunter` → "Royal Encounter", `rainbow_collector` → "Color
Collector", `cat_explorer` → "Cozy Collector", `first_meow` → "First
Paw") — the `key` a user already has unlocked in `user_achievements`
never changes, only the display label/emoji, so nothing "re-locks."
Four new keys: `rare_hunter` (Rare-tier-or-higher, same tiered-threshold
convention as the existing Legendary-or-higher one), `storyteller`
(distinct cats with ≥1 story, *not* total story rows — see §15's
anti-farming note, this reuses the same `STORY_GENERATED` event count
so Regenerate can't inflate it either), `dream_keeper` (a real query
for any Dreamy & Emotional story, `story_repository.has_story_of_style`),
`cat_home` (first favorite).

## 17. Breed Discovery & Collection Completion (Phase 10)

**The canonical "breed universe"** is `ml/models/class_names.json` —
the trained breed classifier's 12-class label set
(`app/services/breed_catalog.py`), chosen because it's committed to
the repo and always present, unlike the trained weights themselves.
This is a fixed, documented denominator; nothing about it is invented
per-request.

**Two different, deliberately separate concepts** both use "breed,"
and conflating them would be dishonest:

- **Discovery moments** (`is_first_of_breed`/`is_first_of_rarity` in
  `analysis_repository.py`) — "has this user ever gotten this exact
  `breed_label` before" — apply to *any* breed string, including
  demo-mode-only labels (`"Domestic Shorthair"`) that aren't in the
  canonical 12. Recomputed fresh from real rows every time (excluding
  the row currently being discovered), never a stored flag, so it can
  never desync from what actually happened.
- **Collection completion** (`CollectionStats.completion_percentage`)
  — `round(100 × unique_breeds_discovered / total_supported_breeds, 1)`
  where `unique_breeds_discovered` is `COUNT(DISTINCT breed_label)`
  *restricted to the canonical 12*. A demo-only breed like "Domestic
  Shorthair" contributes to a user's total cat count but never to this
  percentage — there's no fabricated bonus for a label the classifier
  wasn't actually trained to recognize.

**Honest limitation this creates**: only 4 of the 5 demo-mode breed
labels (`"British Shorthair"`, `"Maine Coon"`, `"Siamese"`, `"Bengal"`
— not `"Domestic Shorthair"`) are canonical, so a user running purely
in demo mode (no ML weights installed) can reach at most 4/12 ≈ 33%
breed completion no matter how many cats they analyze. Documented
here and in PROJECT_STATUS.md rather than hidden; installing the real
breed classifier (`ml/training/train_breed_classifier.py`) is what
unlocks the rest.

**Duplicate cats** (spec §20) are handled by the same
`user_id`-scoped, non-deduplicating queries throughout: `total_cats`
counts every analysis row (two photos of the same breed are still two
separate discoveries, two separate rows in the collection grid).
`unique_breeds_discovered` and `rarity_distribution`
(`analysis_repository.get_rarity_distribution`, zero-filled across all
six tiers) are the only places a repeat breed/rarity *doesn't* add a
second count — verified by `test_gamification.py`'s
`test_duplicate_breed_does_not_inflate_unique_breed_completion` and
the Playwright E2E script's step 6-7.

**Breed Explorer** (`GET /api/v1/me/breeds`) merges the full canonical
12-breed list with this user's real per-breed stats
(`analysis_repository.get_breed_discovery_stats`) — an undiscovered
breed gets `discovered: false`, `count: 0`, `best_confidence: null`,
never a fabricated placeholder pretending the user has analyzed
something they haven't.

## 18. Discovery Moments & the MeowVerse Map (Phase 10)

Discovery toasts (new breed / new rarity / achievement unlocked /
level up) are event-driven, not polled or shown unconditionally — they
ride along on the same `GamificationEvent` a mutation response already
carries (§15), so a toast only ever fires immediately after the action
that earned it, exactly once, with no separate "has this been shown
before" flag to keep in sync (the underlying booleans —
`is_new_breed`, `is_new_rarity`, `leveled_up`, `newly_unlocked` — are
themselves already idempotent-by-construction).

The **MeowVerse Map** (`frontend/features/collection/components/
CollectionMap.tsx`) is a constellation view built from plain SVG +
CSS + Framer Motion — no WebGL/3D engine. Each cat's position is a
deterministic hash of its id (not stored coordinates), so the same cat
always lands in the same spot without a migration or extra column;
capped at 60 nodes for a "feel of the collection" view rather than a
second copy of the paginated grid, which remains the actual browsing
surface. Below the `sm` breakpoint, small scattered SVG touch targets
stop being usable, so a plain list takes over instead (verified via
Playwright responsive screenshots at 320px).

## 19. Visual Similarity Architecture (Phase 11)

**The layering the spec asked for, exactly**:

```
EmbeddingModel  (app/ml/embedding_model.py)
     ↓
CatEmbeddingService  (app/services/embedding_service.py)
     ↓
VectorIndex  (app/similarity/vector_index.py)
     ↓
SimilarityService  (app/services/similarity_service.py)
     ↓
API  (app/api/v1/similarity.py)
     ↓
Frontend  (frontend/features/similarity/)
```

Nothing above `EmbeddingModel` depends on *which* embedding model is
running (a future stronger backbone is a drop-in swap — same
`BaseModel` contract as `BreedClassifier`/`FurColorAnalyzer`); nothing
above `VectorIndex` depends on FAISS specifically (a future
`PgVectorIndex` implements the same four-method interface).

**Embedding model**: `torchvision.models.mobilenet_v3_small` with its
stock **ImageNet-pretrained** weights
(`MobileNet_V3_Small_Weights.IMAGENET1K_V1`) — deliberately *not* this
project's own breed-fine-tuned weights (`app/ml/breed_classifier.py`).
A breed-fine-tuned backbone's features are pulled toward separating
the 12 trained breed classes, which is exactly the "similarity from
breed labels" shortcut the spec forbids (§3); a generic ImageNet
backbone encodes broader visual structure (shape, texture, coloring
pattern, pose) instead. `predict()` runs the image through `features`
+ `avgpool` and stops *before* the 1000-way classification head,
returning the 576-dim globally-pooled feature vector — the standard,
well-established way to get an embedding from an image classifier
without training anything new (spec §2: "do not train a new model
from scratch unless there is a demonstrated need"). No new model was
trained for this phase.

**Preprocessing** (deterministic, identical constants to the breed
classifier for auditability): resize so the shorter edge is
`224 × 1.14 ≈ 255`px, center-crop to 224×224, convert to RGB,
normalize with ImageNet mean/std (`[0.485, 0.456, 0.406]` /
`[0.229, 0.224, 0.225]`). Same image bytes always produce the same
embedding (verified in `test_embedding_model.py`).

**Normalization & similarity metric**: every embedding is L2-normalized
*once*, at the source, inside `EmbeddingModel.predict()` — every
downstream consumer can assume unit-length vectors. For two
unit-length vectors *a*, *b*, the inner product `a·b` **is** cosine
similarity (`cos θ = a·b / (‖a‖‖b‖) = a·b` when `‖a‖=‖b‖=1`) — no
approximation, no invented scale. `FAISSVectorIndex` uses
`faiss.IndexFlatIP` (inner product) specifically so the raw FAISS
score *is* the cosine similarity with no further transform needed.
The one presentation-layer decision: `SimilarCat.visual_similarity =
max(0, cosine_similarity)`, floored at zero only for *display*
purposes (a negative cosine — visually near-opposite in the model's
feature space — has no sensible "-40% similar" UI reading). The
frontend multiplies by 100 and rounds for the "94% visually similar"
label; nothing about breed or color ever enters this number.

**Vector index**: `FAISSVectorIndex`
(`faiss.IndexIDMap2(faiss.IndexFlatIP(576))`) — exact (brute-force),
not approximate, search. At the spec's own target scale ("hundreds or
thousands" of vectors, §22) `IndexFlatIP` search is sub-millisecond
(measured: 0.9ms mean at 24 real indexed vectors — see
PROJECT_STATUS.md for the full latency table) and exact search means
the mathematics documented above are never approximated away for
speed the project doesn't need yet. `IndexIDMap2` (not the plainer
`IndexIDMap`) specifically because it maintains the reverse map that
makes `reconstruct(vector_id)` work — confirmed the hard way: the
plainer wrapper raises `"reconstruct not implemented for this type of
index"` (see PROJECT_STATUS.md's bug log). Reconstruction is how
`SimilarityService` gets a *query* vector for "cats similar to
analysis X" without ever storing the raw 576 floats a second time
anywhere (Postgres included) — the flat index already keeps the exact
vectors; `get_vector()` just reads one back out.

**Persistence**: write-through — every `add`/`remove` immediately
`faiss.write_index`s the whole index to
`data/similarity_index.faiss`. At this scale (a few thousand 576-dim
float32 vectors ≈ a few MB) rewriting the whole file per mutation is
cheap and guarantees the index survives an unclean restart without a
WAL or clean-shutdown hook; a production deployment at much larger
scale would batch/debounce this instead — documented as a known
simplification. On load, a dimension mismatch against the currently
configured embedding model, or a corrupt/unreadable file, marks the
index `is_available = False` rather than silently starting empty or
crashing (spec §21: "fail safely, never return incorrect results").

## 20. Duplicate Images & Content-Hash Deduplication (Phase 11)

`app/models/embedding.py`'s `CatEmbeddingModel` maps one
`cat_analyses` row to a FAISS `vector_id`, keyed by a sha256
`content_hash` of the raw uploaded bytes. `embedding_service.py`'s
`embed_and_index` checks that hash *before* ever calling the embedding
model: if an existing row (same `content_hash`, same
`embedding_model`/`embedding_version`) is found, the new analysis gets
a row pointing at the **same** `vector_id` — no second, redundant
vector is added to FAISS. `vector_id` is deliberately *not* unique on
this table (`analysis_id` is); several analyses can share one vector.
This is why `SimilarityService`'s self-exclusion filters by
`analysis_id`, not `vector_id` — two genuinely different analyses that
happen to share identical image bytes are still two different cats in
the collection and can legitimately appear as (extremely) similar
results to each other, just never to *themselves*.

Removal (`embedding_service.remove_from_index`) is reference-counted:
a FAISS vector is only actually removed once no other
`cat_embeddings` row still references its `vector_id`, so deleting one
duplicate-content analysis never breaks a sibling's search results.
No caller triggers this yet (there is no "delete an analysis" feature
— see PROJECT_STATUS.md), but the method exists, is correct, and is
tested, ready for whenever that feature is built.

## 21. Privacy & Indexing Policy (Phase 11)

**Every cat that gets an embedding is indexed** — there is no separate
public/private FAISS index (spec §9 offers this as an *example*
policy, not a requirement; a single global index was chosen instead,
see below for why this is still safe). **Privacy is enforced entirely
at the `SimilarityService` layer, after retrieval, via the same
ownership-scoped SQL pattern this codebase already uses everywhere
else** (Phase 9 §12): FAISS returns candidate `vector_id`s with no
notion of who owns what; `SimilarityService` resolves those to real
`cat_analyses` rows and applies `_is_eligible(row, viewer_user_id)` —
public, OR authenticated-and-owns-it — to *every single candidate*
before it can reach a response. A guest (`viewer_user_id is None`) has
no "OR" clause at all: only public cats, ever. This is the same
"impossible to accidentally expose" guarantee Phase 9 established for
ownership checks generally, applied to a new resource: the eligibility
check is unconditional and happens exactly once, right before
serialization, not scattered across call sites where one could be
forgotten.

Because eligible-but-ranked-lower candidates could be filtered out
after retrieval (privacy, then optional breed/rarity/favorite
filters), `SimilarityService` over-fetches from FAISS —
`min(k × similarity_candidate_oversample, index.size)` candidates,
default oversample factor 10 — so enough *eligible* results remain
after filtering to actually fill up to `k`. The source cat itself must
also pass the existing "public OR you own it" visibility check (same
one `GET /api/v1/analyses/{id}` uses) before any search runs at all —
you can't probe for "similar cats" on an analysis you can't see in the
first place.

**What's never exposed**: email addresses, internal-only metadata, a
stranger's `is_favorite` status (computed per-candidate from the
*viewer's own* ownership, exactly like `analysis_row_to_result`'s
existing `viewer_is_owner`-gated pattern — Phase 9 §12), private image
URLs (an ineligible candidate never reaches the response to have its
`image_url` read in the first place), or which embedding model
produced a result the caller isn't allowed to see.

## 22. Model Versioning, Reindexing & Index Management (Phase 11)

Every `cat_embeddings` row records `embedding_model`,
`embedding_version`, and `embedding_dim` at the time it was created —
never assumed constant. `EMBEDDING_MODEL_NAME =
"mobilenet_v3_small_imagenet"`, `EMBEDDING_VERSION = "v1"` live in one
place (`app/ml/embedding_model.py`) that everything else reads from.
If a future, stronger embedding model replaces this one, its vectors
are **not mathematically comparable** to v1's (different model,
different feature space) — the version fields are exactly how the
system would know that, and `python -m app.cli.similarity_index
verify` flags every row whose `embedding_model`/`embedding_version`
doesn't match the currently-configured one as **stale**, instructing
a rebuild rather than silently mixing incompatible vectors in one
index.

**Reindexing** is deliberately simple, per the spec's own "keep it
simple and understandable, don't attempt zero-downtime multi-version
indexing unless necessary" (§35): `python -m app.cli.similarity_index
rebuild` clears every `cat_embeddings` row and the FAISS index, then
re-embeds every analysis that has a stored photo, from scratch, with
whatever model is currently configured. No dual-index cutover, no
partial-migration state — a v1→v2 upgrade is "run rebuild," not a
multi-step migration.

**Index management** (`app/cli/similarity_index.py`, spec §20) is a
plain CLI, never an HTTP endpoint a normal user (or even an
authenticated one) could reach:

- `build` — embeds every analysis with a stored photo that doesn't
  have an embedding yet (the normal backfill/catch-up path).
- `rebuild` — clears and re-embeds everything (the model-upgrade path).
- `verify` — consistency checks (spec §21): duplicate
  `analysis_id`→`vector_id` mappings, `cat_embeddings` rows whose
  `analysis_id` no longer exists, stale model/version rows, embedding-
  dimension mismatches, FAISS vectors with no Postgres row pointing at
  them (orphans), and an unavailable/corrupt index. Reports every
  problem found and exits non-zero; never silently repairs anything —
  a silent repair would hide exactly the kind of bug this command
  exists to surface.

Run for real against this project's own accumulated dev database
during Phase 11 (see PROJECT_STATUS.md for the actual numbers):
`build` correctly backfilled 869 previously-unembedded analyses,
`verify` reported zero problems across 980 real embedding rows
afterward.

## 23. Explainable AI: Real Grad-CAM (Phase 12)

**Target model**: `app/ml/breed_classifier.py`'s `BreedClassifier` —
the same fine-tuned MobileNetV3-Small used for the actual breed
*prediction* shown to the user. This is a deliberate difference from
Phase 11's embedding model: Grad-CAM must explain *this specific
prediction*, so it has to run against the exact model that produced
it, not a generic feature extractor. `BreedClassifier.explain()` is a
new method alongside the existing `predict()` — same loaded weights,
same singleton, same `is_available` honesty contract, no second model
to keep in sync.

**Target layer, verified by inspection, not assumed**: a real forward
pass of a 224×224 tensor through `model.features` (the full 13-block
Sequential) produces a `(576, 7, 7)` tensor — confirmed empirically
before writing any Grad-CAM code. `model.avgpool` then collapses that
to `(576, 1, 1)`, destroying every spatial coordinate, and
`model.classifier` (a plain `Linear → Hardswish → Dropout → Linear`
stack) operates purely on the flattened 576-vector with no spatial
structure left at all. That makes `model.features[-1]`
(`GRAD_CAM_TARGET_LAYER = "features.12"`, a `Conv2dNormActivation`
block) the *only* layer in this architecture that is both late enough
to carry high-level, class-discriminative features and early enough to
still have the spatial `(7, 7)` grid Grad-CAM needs to produce a
heatmap at all.

**The algorithm** (Selvaraju et al., 2017 — "Grad-CAM: Visual
Explanations from Deep Networks via Gradient-based Localization"),
implemented directly with PyTorch forward/backward hooks (not a
wrapper library — `pytorch-grad-cam` is pre-staged in
`requirements-ml.txt` from early planning but was deliberately not
used, in favor of a from-scratch implementation whose every step is
auditable and independently testable, matching this codebase's
established preference for owning its core algorithms — see `bcrypt`
over `passlib`, Phase 9):

1. Forward pass through the full model, capturing `features[-1]`'s
   output via a forward hook (real activations, `(576, 7, 7)`).
2. Pick the target class logit — the caller's explicit `target_class`,
   or (default) the breed already shown to the user for this analysis.
3. Backward pass from *only* that one logit. A backward hook on
   `features[-1]` captures the real gradients flowing back to it,
   `(576, 7, 7)` — "how much would this one class's score change if
   each activation here changed."
4. Global-average-pool the gradients over the spatial dimensions →
   one importance weight per of the 576 channels.
5. Weight each channel's activation map by its coefficient and sum
   across channels → a single `(7, 7)` importance map
   (`torch.einsum("c,chw->hw", weights, activations)`).
6. ReLU — keep only *positive* contributions to the target class.
7. Min-max normalize to `[0, 1]` (an all-zero map in the degenerate
   case where nothing contributed positively at all — never fabricated
   as if something had).
8. Bilinear-resize from `(7, 7)` up to the *original* photo's actual
   pixel dimensions (`torch.nn.functional.interpolate`).

Verified against real trained weights (`ml/models/breed_classifier.pt`,
Phase 4's training run) with real Oxford-IIIT Pet photos before this
was considered done — see PROJECT_STATUS.md for the actual numbers,
including a real misprediction (Bengal → Egyptian Mau) reported
honestly rather than hidden.

**Faithfulness sanity check** (spec §27, optional, implemented since
the pipeline made it practical): masking the top 15% of a photo's
heatmap with the image's own mean color and re-running the classifier
for the *same* target class showed a real mean confidence drop of
+0.558 across 5 real British Shorthair photos — 4 dropped
substantially (two even flipped the model's top-1 prediction to a
different breed entirely), one barely moved. This is reported as
exactly what it is: a sanity check that the heatmap correlates with
what the model actually relies on, never as proof that the highlighted
region *causes* the prediction (masking also changes surrounding
context/composition, and a CNN's response to a modified image isn't
strictly decomposable into "what changed").

**Confidence vs. Grad-CAM intensity — never conflated**: `confidence`
is a single scalar, the model's own softmax probability for the target
class (identical concept to `AnalysisResult.breed.confidence`). The
heatmap is a full `(H, W)` array with no single "score." The API
(`CatExplanation`), the DB row (`CatExplanationModel`), and the UI
(`GradCamExplanation.tsx`) all keep these as two visually and
structurally separate things — the UI shows "Prediction confidence:
91%" as plain text, never a claimed property of the colorized image
next to it.

**Visualization**: `app/ml/heatmap_visualization.py` colorizes the
normalized heatmap with OpenCV's `COLORMAP_JET` (the same scale the
original Grad-CAM paper's own figures use — not an invented one:
blue = low importance, red = high). The overlay blends it onto the
original photo with **per-pixel alpha proportional to that pixel's
importance** (`alpha = heatmap_value × 0.6`), not one flat alpha —
low-importance regions stay close to the original photo, and even the
single hottest pixel is capped at 60% blend, so the source photo is
never fully hidden (spec §10).

## 24. Explanation Storage, Privacy & Caching (Phase 12)

**Storage**: reuses `ImageStorageProvider` (Phase 9) — no second
storage system. Phase 12 adds exactly one new capability to the
interface, `load(url) -> bytes | None`, the inverse of `save()`,
needed because Grad-CAM has to re-read the *original* uploaded photo
back out of storage to run inference on it (the analyze pipeline never
kept the raw bytes around after the initial request).
`LocalImageStorageProvider.load()` reverses a `/media/<file>` URL back
to a filesystem path, with an explicit path-traversal guard
(`resolved.is_relative_to(directory)`) before ever reading — the URL
technically originates from a DB column, but nothing in this pipeline
should ever trust a stored string enough to skip that check. The
generated heatmap/overlay PNGs are saved through the exact same
`storage.save()` every uploaded photo goes through; the API only ever
returns the resulting `/media/...` URLs, never a filesystem path.

**Privacy**: identical rule to every other analysis-scoped endpoint —
the source analysis must be visible to the caller (public, or owned by
an authenticated caller) *before* anything else happens, checked via
the same `get_public_analysis`/`get_owned_analysis` ownership-scoped
queries Phase 9 established. A 404 for "doesn't exist" and "exists but
isn't yours" are identical, same anti-enumeration principle as
everywhere else. This check happens first, ahead of even checking
whether the analysis is in demo mode — a private demo-mode analysis
gets the same 404 as a private trained one; only a caller who's
already allowed to see the cat at all learns *why* no heatmap exists
for it.

**Never a fake explanation for a demo prediction**: `breed_mode` is
checked on the *stored analysis row*, not re-derived from whether the
classifier happens to be loaded right now — an analysis created while
the classifier was unavailable (`breed_mode: "demo"`) stays honestly
unexplainable forever, even if the classifier becomes available again
later, because that analysis's displayed breed was never a real
prediction to begin with.

**Caching** (spec §13): `CatExplanationModel` is unique on
`(analysis_id, target_class, breed_model_version)`. A second request
for the same analysis + same target class + same classifier version
reuses the row (`cached: true` in the response) instead of running
Grad-CAM again — a real forward+backward pass is too expensive to
repeat on every page view. A different `target_class` gets its own
row (a genuinely different artifact). A retrained classifier (bumped
`BreedClassifier.version`) simply won't match any existing row, so a
fresh, correctly-versioned explanation gets generated automatically —
no explicit "invalidate the old ones" step needed, the cache key
itself makes staleness self-resolving, same pattern as Phase 11's
embedding-model versioning.

**On-demand only** (spec §31): nothing about Grad-CAM runs during
`POST /api/v1/analyses` — `analyze_image()` is unchanged by this
phase. Generation happens exclusively inside
`POST /api/v1/analyses/{id}/explanation`, triggered only when a user
clicks "Why this breed?" in the frontend (`GradCamExplanation.tsx`
uses a manually-triggered `useMutation`, deliberately not an
auto-fetching `useQuery` the way Phase 11's "Cats Like This" is) —
keeping every analyze request's latency unaffected by a feature most
views of a given cat will never invoke.
