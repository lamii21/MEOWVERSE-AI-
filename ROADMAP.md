# MeowVerse AI — Roadmap

Legend: ⬜ not started · 🟨 in progress · ✅ done

## Phase 0 — Repository Inspection & Planning
- ✅ Inspect repository (empty, greenfield)
- ✅ ARCHITECTURE.md
- ✅ PROJECT_STATUS.md
- ✅ ROADMAP.md (this file)

## Phase 1 — Project Architecture Init ✅
- ✅ Frontend scaffold (Next.js 16 + TS + Tailwind v4 + shadcn/ui + Framer Motion + TanStack Query)
- ✅ Backend scaffold (FastAPI + Pydantic + SQLAlchemy async + Alembic), layered per ARCHITECTURE.md (api/core/models/schemas/repositories/services/ml/ai/workers/utils)
- ✅ `BaseModel` (ml) and `LLMProvider`/`ImageGenerationProvider` + null fallbacks (ai) interfaces stubbed as integration points
- ✅ PostgreSQL + Redis + backend + frontend via Docker Compose — verified end-to-end (`/ready` reports both DB and Redis healthy)
- ✅ `.env.example` for both apps, real `.env` gitignored
- ✅ GitHub Actions CI (frontend: lint + build; backend: ruff + pytest)
- ✅ Verified: backend tests pass, ruff clean, frontend lint clean, `pnpm build` succeeds, full Compose stack healthy

## Phase 2 — Design System & Landing Page ✅
- ✅ Design tokens: custom magic (violet) + peach pastel scales (50–900),
  soft-lavender neutrals, `--radius: 1rem`, Quicksand heading font
  alongside Geist Sans body, aurora gradient + glassmorphism utilities
- ✅ Landing page: navbar, hero, how-it-works, AI capabilities (real CV
  vs AI-generated content clearly labeled), example cat card (clearly
  labeled "not a real analysis"), tech stack, FAQ accordion, CTA, footer
- ✅ Hand-crafted animated SVG cat mascot with floating + sparkle
  animations (Framer Motion), respects `prefers-reduced-motion`
- ✅ Verified in a real headless browser (Playwright, no project skill
  existed yet so the generic browser-driven pattern was used): desktop
  light, desktop dark, and mobile (375px) — zero console errors, FAQ
  accordion interaction confirmed working
- ✅ Found and fixed real bugs during verification (see "Notes" below):
  Base UI `Button` `nativeButton` a11y warning, dark mode never
  activating (dead `.dark` class with no toggle), incomplete peach
  color scale silently dropping utilities, and a text-contrast bug on
  the collectible card in dark mode

## Phase 3 — Upload & Analysis Workflow ✅
- ✅ Backend `POST /api/v1/analyses`: validates content-type, size
  (`MAX_UPLOAD_SIZE_MB`), and decodability (Pillow) of the upload;
  returns a deterministic demo-mode `AnalysisResult` (`mode: "demo"`,
  breed + fur palette from a fixed pool, hashed from image bytes so
  the same photo always yields the same demo result). 8 backend tests
  (valid image, unsupported type, corrupt bytes, oversized, too-small,
  determinism). Real model wiring is Phase 4 — the demo function is
  explicitly documented to be deleted, not extended, at that point.
- ✅ `/discover`: drag & drop, file picker, and a dedicated mobile
  camera-capture button, client-side validation (type/size/min
  dimensions) mirroring the backend, preview with replace, friendly
  inline errors.
- ✅ `/analyze`: staged animated loading experience (rotating
  "Finding whiskers...", "Writing your cat's story...", etc., progress
  bar, sparkles, cat emoji, respects `prefers-reduced-motion`), a demo
  result summary explicitly marked "Demo mode" and noting the full
  magical results page is a later phase, and a friendly "no photo yet"
  fallback when the page is visited directly.
- ✅ Verified with a real, scripted browser flow (Playwright driving a
  live `pnpm dev` + `uvicorn` pair): upload → analyze → demo result,
  end to end, network request confirmed hitting the backend and
  returning 200. Found and fixed a real bug in the process (see notes
  below) rather than accepting a screenshot at face value.

## Phase 4 — Breed Classification (real CV) ✅
- ✅ Dataset: Oxford-IIIT Pet (CC BY-SA 4.0), both official splits
  combined then re-split 70/15/15 by `ml/scripts/prepare_dataset.py`,
  filtered to the 12 cat breeds via the dataset's own binary cat/dog
  label (not name casing — this torchvision version Title-Cases every
  breed name, which would have misclassified dog breeds as cats).
  **2,371 real images**, balanced 184–200 per class. Verified file
  counts on disk match `dataset_info.json` exactly.
- ✅ Training: `ml/training/train_breed_classifier.py` — MobileNetV3-Small
  (ImageNet-pretrained, fully fine-tuned), AdamW + cosine LR, 15 epochs,
  CPU (no CUDA wheel fit in the available bandwidth — see PROJECT_STATUS.md).
  **89.24% best validation accuracy**, ~18.4 min total, ~6MB weights file.
- ✅ Evaluation: `ml/evaluation/evaluate.py` on the held-out **test**
  split (360 images, never seen during training/val) —
  **87.50% accuracy, 0.8747 macro F1**. Full per-class precision/
  recall/F1 and confusion matrix saved to
  `ml/evaluation/evaluation_report.json` (tracked in git; not
  fabricated — see the report file for exact numbers). Confusion
  pattern is visually sensible (Sphynx: 100% recall, zero confusion,
  visually unique; Birman↔Ragdoll and Bengal↔Egyptian Mau are the
  main confusions, both genuinely similar-looking breed pairs).
- ✅ `BaseModel` interface + `BreedClassifier` (`app/ml/`), loaded as a
  lazy process-wide singleton, `is_available` gates a graceful demo
  fallback (missing weights, or torch/torchvision not installed at all).
- ✅ `AnalysisResult` split into independent `breed_mode`/`colors_mode`
  (see Phase 3 entry / ARCHITECTURE.md §4) — required precisely because
  breed went real in this phase while fur color was still demo-only
  (colors went real too in Phase 5, immediately below).
- ✅ Verified end-to-end: real backend request with two real held-out
  test photos → correct breed, `breed_mode: "trained"`,
  `colors_mode: "demo"` at the time (independent, as designed — see
  Phase 5 for colors going real); same photos driven
  through the actual browser UI (upload → analyze → result) showing a
  "Real prediction" badge on breed and a "Demo mode" badge on fur
  color; full backend suite (13 tests, including a real-weights
  integration test that only runs when weights are present) and
  frontend build both pass.
- ⚠️ Known gap: the Docker backend image only installs
  `requirements.txt`, not `requirements-ml.txt` — the containerized API
  currently always runs in demo mode. Local (non-Docker) dev has the
  real model. Not fixed in this phase; noted rather than hidden.

## Phase 5 — Fur Color Analysis ✅
- ✅ `FurColorAnalyzer` (`app/ml/fur_color.py`), implementing the same
  `BaseModel` contract as `BreedClassifier` for consistency, even
  though there are no weights to download — `is_available` reflects
  whether opencv/numpy/scikit-learn are importable, degrading to the
  demo palette otherwise rather than crashing.
- ✅ Real algorithm: GrabCut foreground segmentation (rejects background
  before clustering, degrades gracefully to whole-image if the mask
  ends up degenerate) → K-means (k=3, fixed `random_state` for
  determinism) on the foreground pixels → each cluster centroid mapped
  to the nearest name in a small fur-relevant reference palette (not a
  generic CSS color list) via RGB nearest-neighbor — an explicitly
  documented approximation, not a color-science claim.
- ✅ `colors_mode` now goes `"trained"` independently of `breed_mode`
  exactly as the Phase 4 schema split was built to allow — verified
  both signals can be real/demo in any combination via 4 isolated
  mocked tests, and both real simultaneously via the live API.
- ✅ Real-photo sanity check, not just synthetic fixtures: the British
  Shorthair test photo (a breed famous for its "British Blue"
  blue-gray coat) extracted to charcoal/blue/lilac — a striking, honest
  match to the real breed standard. The Siamese photo extracted to
  silver/gray/charcoal rather than the breed-standard cream — checked
  the source photo and confirmed this is a legitimate reading of a
  real, shadowed/backlit outdoor shot, not a bug (documented in
  PROJECT_STATUS.md as an example of real-world variance).
- ✅ 5 new backend tests (availability contract, raises when unloaded,
  3-swatch shape with percentages summing to ~100%, dominant-color
  plausibility on a solid image, color-naming spot checks). Full suite:
  **20/20 backend tests passing.**
- ✅ Verified end-to-end through the actual browser UI: both "Predicted
  breed" and "Fur palette" now show a "Real prediction" badge
  simultaneously for the same real photo.

## Phase 6 — AI Profile Generation ✅
- ✅ `LLMProvider` ABC corrected to typed signatures
  (`generate_profile(CatSignals) -> CatProfile`, was raw `dict[str,
  Any]` since Phase 1) + `LLMProviderError`; `NullLLMProvider` unchanged
  in spirit. `generate_story` removed from the ABC for now — no
  `CatStory` schema exists yet, re-added properly in Phase 7 rather
  than stubbed with a placeholder type today.
- ✅ `AnthropicLLMProvider` (`app/ai/anthropic_provider.py`): real
  `anthropic` SDK (0.121.0) calls using **forced tool use** — the tool's
  `input_schema` is generated directly from `CatProfile.model_json_schema()`,
  so the model literally cannot return anything but that shape (or the
  call fails validation and retries). One semantic retry on invalid
  schema/missing tool call; transport failures (timeout/connection/
  status errors) are not retried at this layer and surface immediately
  as `LLMProviderError` so the caller can fall back quickly.
- ✅ `CatSignals`/`CatProfile` strict Pydantic schemas
  (`app/schemas/profile.py`). `CatProfile` structurally has **no**
  breed/color/confidence fields — the LLM cannot overwrite real CV
  output because the schema gives it nowhere to put it, not because a
  prompt asked nicely. Verified with a dedicated test
  (`test_profile_never_overwrites_real_cv_signals`).
- ✅ `profile_service.py`: calls the provider when available, catches
  `LLMProviderError` and falls back to one of 5 hand-written demo
  profiles (selected deterministically from the image-bytes hash, same
  pattern as the Phase 3/4/5 CV demo fallbacks) — never raises, never
  blocks the analysis endpoint.
- ✅ `AnalysisResult.profile_mode` uses **`"demo" | "generated"`**,
  deliberately different vocabulary from `breed_mode`/`colors_mode`'s
  `"demo" | "trained"` — the profile is never a "prediction," so it's
  never allowed to be labeled with words that imply it is one.
- ✅ Security: `ANTHROPIC_API_KEY` env-var only, empty in
  `.env.example`, never touches the frontend (backend-only calls),
  `anthropic`/`httpx`/`httpcore` loggers pinned to `WARNING` so no
  request/auth data can leak into logs regardless of the app's debug
  level.
- ✅ Limits: `ANTHROPIC_MAX_OUTPUT_TOKENS` (1024), `ANTHROPIC_TIMEOUT_SECONDS`
  (20s), a hard 2000-char prompt-size ceiling (defensive — all inputs
  come from our own bounded CV output, never raw user text, so
  practically unreachable but real and enforced), and a simple
  in-memory per-IP rate limiter (`RATE_LIMIT_PER_MINUTE`, default 20)
  on `POST /api/v1/analyses` specifically, since it's the only endpoint
  that can trigger a paid external call.
- ✅ 14 new backend tests covering every required scenario: valid
  response, missing tool_use block (retries then fails), invalid schema
  (retries then recovers / retries then fails), API timeout, API
  connection error, API status error, missing API key → `NullLLMProvider`,
  configured key → `AnthropicLLMProvider`, provider-unavailable
  fallback, provider-success passthrough, provider-failure fallback,
  demo-fallback determinism, and a 429-after-threshold rate-limit test.
  **35/35 backend tests passing**, Phase 1–5 tests unchanged and green.
- ✅ Frontend: `DemoResultSummary` renders the full profile (name,
  title, rarity/season badges, personality, magic power, kingdom,
  favorites, description) with a **distinct** `ProfileModeBadge`
  ("✨ AI-generated" / "Offline demo content") that never reuses the CV
  signals' "Real prediction" wording or color. New `HowMeowVerseKnows`
  component: a collapsed-by-default accordion explaining each signal's
  real source (breed → CV model, colors → OpenCV+K-means, personality/
  magic power → generative AI), color-coded to match. `AnalysisLoader`
  gained LLM-flavored staged messages ("Learning your cat's
  personality...", "Choosing a magical destiny...").
- ✅ Verified end-to-end through the live API and the actual browser
  UI (no API key configured on this machine, so this exercised the
  real fallback path, not a mock): breed/colors unchanged from Phase
  4/5 (still `"trained"`, same values), `profile_mode: "demo"` with a
  complete, valid profile, "Offline demo content" badge rendering
  correctly, accordion expands and explains all four signals, zero
  console errors.
- ⚠️ Not done this phase (explicitly out of scope per the phase brief):
  image generation, story generation (`CatStory`/Phase 7).

## Phase 7 — AI Story Generation ✅
- ✅ `CatStory` schema (`app/schemas/story.py`): title, subtitle,
  opening, 3–5 chapters, ending, moral, quote — all length-bounded.
  Five `StoryStyle` values (Magical Adventure, Cozy & Wholesome, Funny
  & Chaotic, Dreamy & Emotional, Fantasy Quest), each with an
  emoji/label/description shared by backend (`STORY_STYLE_LABELS`) and
  frontend (`STORY_STYLE_OPTIONS`).
- ✅ `generate_story` back on the `LLMProvider` ABC with the real
  schema (was removed in Phase 6 pending this). `AnthropicLLMProvider`
  implements it via the same forced-tool-use pattern as profiles,
  sharing one generic `_call_tool()` retry helper with
  `generate_profile` instead of duplicating the loop.
- ✅ `app/ai/story_prompt.py`: composable, independently unit-tested
  prompt builder — system rules, safety rules (no sexual/violent/
  hateful/dangerous/medical/political content, no copyrighted
  characters), per-style tone instructions, and a cat-context builder
  that explicitly labels which signals are real CV output vs.
  fictional/creative so the model never treats its own invented detail
  as fact.
- ✅ `story_service.get_or_generate_story`: on-demand generation only —
  returns the existing `(analysis_id, style)` story unless
  `regenerate: true` is explicitly passed (no silent
  auto-regeneration, no provider call at all for a duplicate request).
  Deterministic offline fallback (`story_templates.py`, SHA-256 of
  analysis id + style) with a `variant_offset` so Regenerate visibly
  cycles template variants even without a live provider.
- ✅ `story_mode` (`"demo" | "generated"`) reuses `profile_mode`'s
  deliberately non-"prediction" vocabulary.
- ✅ Cost control: `MAX_STORY_PROMPT_CHARS` (3000), same
  `ANTHROPIC_MAX_OUTPUT_TOKENS`/`ANTHROPIC_TIMEOUT_SECONDS` as
  profiles, story endpoint added to the existing rate limiter.
- ✅ **New in this phase: minimal real Postgres persistence** —
  `cat_analyses`/`stories` tables (Alembic migration), ahead of the
  full Phase 9 schema, because the story feature is inherently
  `analysis_id`-based lookup. Analysis persistence is best-effort
  (`AnalysisResult.id: UUID | None`); the core analyze endpoint never
  depends on the DB. `stories.is_public` (default `False`) +
  `POST /api/v1/stories/{id}/share` (idempotent, explicit) back a real
  `/story/[id]` public share page — not just architecture prep.
- ✅ API: `POST /api/v1/analyses/{id}/story` (rate-limited),
  `GET /api/v1/stories/{id}` (404 unless public),
  `POST /api/v1/stories/{id}/share`.
- ✅ Frontend: `StoryStyleSelector` (5 selectable cards), `StoryLoader`
  (staged messages: "Opening the Cat Universe...", "Finding a little
  bit of magic...", "Writing your cat's first adventure...", "Choosing
  the perfect ending..."), `StoryCard` (progressive Framer Motion
  reveal — title → opening → chapters → ending → moral → quote,
  respects `prefers-reduced-motion`, a `StoryModeBadge` matching
  Phase 6's `ProfileModeBadge` styling, Favorite/Share/Download/Print/
  Regenerate actions — all genuinely functional, not stubs: Favorite
  persists to `localStorage` via `useSyncExternalStore`, Share calls
  the publish endpoint and copies the link, Download saves a real
  `.txt` file, Print calls `window.print()`), `StorySection`
  orchestrator (idle → pending → success/error, explicit Generate/
  Regenerate only), `/story/[id]` public page (server component,
  `notFound()` for private/missing stories).
- ✅ Testing infrastructure added from scratch — **no frontend test
  tooling existed before this phase.** Vitest + React Testing Library,
  `pnpm test`. 24 new frontend tests (style selector, loader, story
  card incl. favorite/share/regenerate/mode-badge behavior, section
  state machine incl. error/regenerate flows, API client incl. every
  error-kind branch). Backend: 75/75 passing (was 72 — 3 new tests for
  the share endpoint added mid-phase once real sharing was built,
  beyond the original "architecture prep only" scope).
- ✅ Verified end-to-end via a live Playwright run against real
  `uvicorn`/`next dev` servers (no project run-skill existed yet, so
  the generic browser-driven pattern was used): upload → analyze →
  style selection → generate → progressive reveal → regenerate →
  favorite → share → open the `/story/[id]` link → download. Zero
  console errors on the **final** run — but the *first* run surfaced
  three real bugs, all found and fixed, not glossed over: (1) a
  pre-existing Phase 6 duplicate-React-key warning on fur-color
  swatches sharing a hex value, (2) a genuine SSR/hydration mismatch
  in the new favorite-button state (read `localStorage`, unavailable
  during SSR — fixed by switching to `useSyncExternalStore` with an
  explicit `false` server snapshot instead of a `useEffect`), and (3) a
  double-quoted pull-quote (demo templates and the on-screen render
  each added their own quote marks) — fixed at the template source and
  hardened defensively in the renderer for the real-LLM path too.
- ✅ No API key configured on this machine — same honest gap as Phase
  6: real code against the verified SDK surface, 13 dedicated mocked
  tests (9 profile + 4 story) covering the Anthropic provider, but the
  first live call should still be watched.
- ⬜ Not done this phase (explicitly out of scope per the phase brief):
  image generation (Phase 13).

## Phase 8 — Magical Experience & Cat Card ✅
- ✅ Cinematic reveal (`ResultReveal`): timed intro ("A new cat has
  appeared...", glow behind the photo) → the Cat Card's own internal
  Framer Motion stagger (rarity → image → name → breed → magic power →
  confidence → palette) → story availability → the card becomes
  interactive (tiltable) only once fully settled. `prefers-reduced-motion`
  skips straight to the finished, fully interactive state rather than
  gating content behind timers — verified with real Playwright
  `reducedMotion: "reduce"` emulation, not just code inspection.
- ✅ **Cat Card** (`features/results/components/CatCard.tsx`): image,
  name, title, breed, rarity badge, magic power, personality, fur
  palette, description, MeowVerse ID (short id derived from the
  analysis UUID) — no "mood" field, since none exists in `CatProfile`
  and nothing here is fabricated to fill the spec's "if available"
  slot.
- ✅ Six-tier rarity visual system (`features/results/rarity.ts` +
  `RarityAura.tsx`): Common (plain) → Uncommon (tint) → Rare (shimmer
  sweep) → Epic (gradient glow) → Legendary (pulsing aura) → Mythical
  (twinkling particles) — each tier a strict superset of polish over
  the last, deliberately subtle (no flashing), every animated variant
  has a static reduced-motion equivalent.
- ✅ Card interaction: pointer-driven 3D tilt via Framer Motion springs
  + CSS transforms (`use-card-tilt.ts`, no WebGL), disabled on touch
  pointers and under reduced motion; `whileTap` scale feedback on
  mobile.
- ✅ Card actions, all genuinely functional: Save (local bookmark,
  `useSyncExternalStore`-backed — deliberately consolidated with the
  brief's separate "Favorite" action, since neither has a collection
  page to view against yet, Phase 10), Share (marks the analysis
  public + native share sheet with clipboard fallback), Download PNG
  (`html-to-image`, see below), Generate Story (scrolls to the
  existing Phase 7 `StorySection`), Generate Wallpaper (disabled,
  labeled "Coming in a future update" — placeholder only, as the brief
  specified).
- ✅ Reliable PNG export: real gotcha found and fixed, not just handled
  in the abstract — `cacheBust: true` appends a `?timestamp` query
  string to every image src, which breaks `blob:` URLs (the uploaded
  photo's src) since they don't support query strings at all; removing
  it fixed exports that were throwing on every attempt. Export failures
  surface as an inline "Download failed" state, never a blank/broken
  file. Self-hosted fonts (`next/font`) sidestep the font-CORS class of
  failure entirely.
- ✅ **New backend addition**: `cat_analyses.is_public` +
  `GET/POST /api/v1/analyses/{id}` `/share` (migration `d64ea3d2f0bd`),
  mirroring Phase 7's story-sharing pattern exactly, backing a real
  `/cat/[id]` public Cat Card page (server component, `notFound()` for
  private/missing) — not left as "architecture prep only."
  6 new backend tests; **81/81 backend tests passing** (was 75).
- ✅ Confidence shown as a labeled "Model confidence" meter with an
  always-visible explanation ("not a certainty claim about your cat's
  actual breed") — never implying identity certainty.
- ✅ Fur palette turned into a designer-style presentation: a
  proportional stacked strip plus per-swatch name/hex/percentage.
- ✅ "How MeowVerse knows this" (Phase 6) kept and visually regrouped
  into two clearly labeled sections — "Real computer vision" vs
  "Generative AI" — rather than only distinguishable by icon color.
- ✅ Responsive: two-column desktop layout (Cat Card sticky-left, story
  + transparency panel right) collapsing to single-column at `lg`
  and below; verified at 320/375/390/768/1024/1440px via Playwright.
- ✅ Frontend testing: 27 new tests (rarity config completeness/tier
  ordering, ConfidenceMeter labeling, ColorPalette rendering,
  `useCardTilt` reduced-motion branches, `ResultReveal` stage
  transitions incl. reduced motion, and a comprehensive `CatCard` suite
  covering rendering, Save, Share incl. native-share vs clipboard
  fallback vs error, Download incl. failure state, Generate Story
  scroll, and the disabled Wallpaper placeholder). **51/51 frontend
  tests passing** (was 24).
- ✅ Verified end-to-end via a live Playwright run against real
  `uvicorn`/`next dev` servers, covering the full brief: landing →
  upload → analyze → cinematic reveal → Cat Card → tilt hover → Save →
  Share → Download PNG → Generate Story → open the shared `/cat/[id]`
  link → responsive breakpoints → reduced-motion emulation. **Zero
  console errors on the final run** — but, as with every prior phase,
  earlier runs surfaced real bugs that got fixed rather than glossed
  over:
  1. `cacheBust: true` breaking PNG export on `blob:` image sources
     (above).
  2. A genuine `useReducedMotion()` race: reading it directly in a
     `useState` initializer captures the hook's SSR-safe default
     (`false`) before its own internal effect resolves the real value,
     so the reveal always played the full animated sequence once
     regardless of the actual OS preference on first render. Fixed
     with a syncing `useEffect`.
  3. A pre-existing, previously-undiscovered CSS bug from Phase 2:
     `--font-sans: var(--font-sans)` in `globals.css` is
     self-referential (should reference `--font-geist-sans`), so the
     entire app had silently been falling back to the browser's
     default serif font instead of Geist Sans since the design system
     was first built. Caught only because Phase 8's typography focus
     (§11) prompted a close visual look at rendered text.
  4. The shared `Progress` UI primitive (`components/ui/progress.tsx`)
     always renders its own default track+indicator *in addition* to
     any children passed to it — `ConfidenceMeter`'s custom-styled
     track therefore rendered as two stacked bars. Fixed by dropping
     the custom children and using the component's default styling.
  5. The magic-power `Badge` overflowed and clipped its text off the
     edge of the card — `Badge` is `whitespace-nowrap` by design (built
     for short tags), but `magic_power` can be a full sentence. Fixed
     by rendering it as wrapping plain text instead of a badge.
- ⬜ Not done this phase (explicitly out of scope per the phase brief):
  new ML models, authentication, image generation, vector database
  migration, advanced analytics.

## Phase 9 — Authentication, User Accounts & Persistent Cat Collection ✅
- ✅ Real `users`/`sessions`/`user_achievements` tables + `cat_analyses`
  ownership/favorite/rarity/image columns (migration `b04f6df3d75b`,
  chained off Phase 8's head, not a fresh baseline — see
  ARCHITECTURE.md §6). Verified against the actual populated dev DB:
  upgrade (with a real data backfill for 341 pre-existing rows),
  downgrade, re-upgrade, data integrity checked after each step.
- ✅ Email/password auth: register/login/logout/me
  (`POST/GET /api/v1/auth/*`), bcrypt password hashing (not
  `passlib[bcrypt]`, which is pre-staged since Phase 1 but confirmed
  broken against this project's installed bcrypt 5.x before writing
  any auth code), DB-backed opaque session tokens in an httpOnly
  `SameSite=Lax` cookie — not JWT, despite `python-jose` also being
  pre-staged; see ARCHITECTURE.md §11 for the full security-decision
  writeup the spec asked for.
- ✅ Server-side ownership enforcement, not just frontend route
  guards: every private-resource repository function
  (`get_owned_analysis`/`get_owned_story`, `claim_analysis`,
  `set_favorite`, `set_public`/`set_private`) filters by `user_id` at
  the query level, so a query simply cannot return another user's
  private row — not a check that a future endpoint could forget.
  Verified with a dedicated cross-user test suite
  (`tests/test_ownership.py`): guest can't view a stranger's private
  cat, a second user can't view/favorite/share/unshare a first user's
  cat, claiming an already-owned cat fails with 409.
- ✅ Guest experience fully preserved: upload/analyze/view/generate
  stories all still work with no account — an authenticated request
  auto-owns its analysis immediately (no separate save step), a guest
  analysis is created unowned and stays fully functional, just
  invisible to any collection query until explicitly claimed via
  `POST /api/v1/analyses/{id}/save` after registering — which also
  means demo/anonymous browsing can never silently become a permanent
  record (spec §17), since stats/achievements queries only ever see
  owned rows in the first place.
- ✅ Real image persistence: `ImageStorageProvider` abstraction
  (`app/storage/`) + a genuine `LocalImageStorageProvider` (not a
  stub — the collection page needs the photo to survive a refresh),
  served via a `/media` static mount, interface shaped for a later
  S3-compatible swap with no caller changes.
- ✅ Collection: `GET /api/v1/me/collection` (filter by rarity/favorites,
  search by name/breed, sort newest/oldest/rarity/name, paginated) +
  `GET /api/v1/me/stats` (total cats, favorite breed, most common
  color, legendary+ count, favorites count, stories created — every
  number a real query scoped to `user_id`, never fabricated) +
  `GET /api/v1/me/achievements` (5 achievements — 🐾 First Meow, 🌸 Cat
  Explorer, 💎 Collector, 🌈 Rainbow Collector, 👑 Legendary Hunter —
  compute-on-read against real stats, code-defined criteria, DB-persisted
  unlock events).
- ✅ Public sharing now ownership-gated: `POST .../share` and the new
  `POST .../unshare` (for both analyses and stories) require owning
  the resource — previously (Phase 7/8) open to anyone holding the id,
  since no auth existed yet to check against. Public responses never
  leak `is_favorite`/`owned` to a non-owner viewer — a real bug caught
  during this phase's own testing (`viewer_is_owner` is now a required
  kwarg with no default on the row→response converter, so no call site
  can forget which case it's in).
- ✅ CSRF: `SameSite=Lax` cookie as primary defense + an `Origin`-header
  check dependency (`verify_same_origin`) as defense-in-depth on every
  state-changing authenticated endpoint. Rate limiter refactored behind
  a `RateLimiter` protocol (Redis-swappable later) with a tighter,
  separately-keyed limit on register/login specifically.
- ✅ Frontend: `hooks/use-auth.ts` (TanStack Query as the actual auth
  state store — no separate Context), `/login`/`/register` (on-brand
  copy: "Welcome back, cat explorer.", "Let's find your next little
  friend."), a global auth-aware nav (incl. a real mobile hamburger
  menu — a genuine gap found during responsive QA: the desktop nav
  links had `hidden md:flex` with no mobile alternative at all),
  `GuestSavePrompt` ("Your little friend deserves a home. 🐾"),
  `RequireAuth` route guard, `/collection` (gallery, filters, search,
  sort, empty state with a "Discover a Cat" CTA), `/collection/[id]`,
  `/profile` (stats tiles + achievements list), `/settings` (display
  name, logout). `CatCard`'s Save/Favorite migrated from Phase 8's
  local-only bookmark to real backend mutations with optimistic UI and
  rollback-on-error (`use-cat-actions.ts`).
- ✅ Tests: 65 new backend tests (`test_auth.py`,
  `test_ownership.py`, `test_collection.py`, + auth-related additions
  to `test_analyses.py`/`test_stories_api.py` for the now-ownership-gated
  share endpoints) — **137/137 backend tests passing** (was 81).
  14 new frontend tests (`use-auth`, `GuestSavePrompt`, `RequireAuth`,
  `CollectionCard`, plus a full rewrite of `CatCard.test.tsx` for its
  new TanStack-Query-mutation architecture) — **69/69 frontend tests
  passing** (was 55).
- ✅ Verified end-to-end via a live, scripted Playwright run covering
  the exact 21-step flow the spec laid out (guest analyze → Save →
  guest prompt → register → save → refresh → collection persists →
  open cat → favorite → refresh → favorite persists → share → public
  page → verify no email/favorite/owned leak → logout → protected
  page redirects to login → login again → collection restored) — every
  step passed. A real bug was found and fixed mid-run, not glossed
  over: logging out from a protected page raced a `router.push("/")`
  against `RequireAuth`'s own redirect-to-login effect and could land
  on `/login?next=/settings` right after voluntarily signing out;
  fixed with a hard `window.location.href` navigation instead, which
  also guarantees a fully clean client state. The only console entries
  across the whole run are the browser's own "401 (Unauthorized)"
  network log lines from the guest `/me` check — not a JS error, and
  architecturally unavoidable (httpOnly cookies can't be checked
  client-side before asking the server, so a guest's very first
  page load always includes one legitimate 401).
- ⬜ Not done this phase (explicitly out of scope per the phase brief):
  new ML models, OAuth, image generation, advanced analytics, vector
  database migration.

## Phase 10 — MeowVerse Cat Universe: Collection, Gamification & Discovery ✅
- ✅ "My Cat Universe" collection redesign — header, real stats summary
  (total/favorites/stories/rare+/legendary+/completion%), extended
  filters (rarity tiers, Favorites, Stories, Recently Discovered),
  debounced search (name/breed/color), extended sort (newest/oldest/
  name A-Z/name Z-A/rarity/breed/favorite), pagination.
- ✅ Server-authoritative XP + leveling — 5 XP-awarding event types,
  idempotent via a `collection_events` log (no client-trusted values,
  no farming via repeat favorite/unfavorite or Regenerate spam), a
  documented quadratic level curve capped at level 20. See
  ARCHITECTURE.md §15.
- ✅ Achievement engine extended to 9 (from Phase 9's 5) — Rare Hunter,
  Dream Keeper, Storyteller, Cat Home added; existing keys relabeled
  (never renamed at the DB level) to match this phase's naming. Real
  progress bars (`progress_current`/`progress_target`) on locked ones.
  See ARCHITECTURE.md §16.
- ✅ Breed Explorer — the full canonical 12-breed universe
  (`ml/models/class_names.json`), undiscovered breeds shown locked with
  zero fabricated stats. Collection completion % defined and documented
  precisely (unique canonical breeds / 12). See ARCHITECTURE.md §17.
- ✅ MeowVerse Map — an original SVG/CSS/Framer-Motion constellation
  view (no 3D engine), deterministic per-cat star positions, a simpler
  list fallback below the `sm` breakpoint. See ARCHITECTURE.md §18.
- ✅ Event-driven discovery toasts (new breed / new rarity / achievement
  unlocked / level up) — never the same toast shown twice for the same
  moment, queued one-at-a-time, reduced-motion-aware.
- ✅ `/achievements` page (unlocked + locked-with-progress), `/profile`
  upgraded (level/XP bar, 8 real stats, favorite cat preview).
- ✅ Duplicate-cat handling defined and tested: total cats counts every
  analysis; unique breeds/completion% never double-count a repeat
  breed. See ARCHITECTURE.md §17 and `test_gamification.py`.
- ✅ Backend: 170/170 tests (was 140), ruff clean. Frontend: 85/85 tests
  (was 69), lint/build clean. Full 22-step Playwright E2E flow passing
  against real dev servers, responsive QA at 320–1440px (zero
  horizontal overflow), reduced-motion verified.
- 🐛 Found and fixed during this phase's reduced-motion QA (not
  hypothetical, not introduced this phase): `AuthCard.tsx` (Phase 9)
  conditioned its Framer Motion `initial` prop on `useReducedMotion()`,
  which is read differently between SSR and a client whose OS already
  prefers reduced motion — a genuine hydration mismatch on `/login` and
  `/register`'s first paint. Fixed by keeping `initial` constant and
  only gating the transition `duration`, which is SSR-safe.
- ⬜ Delete (remove a cat from your collection) — still not built; same
  reasoning as Phase 9 (cascading a shared/public cat's story and link
  deserves its own deliberate decision, not a bolt-on here either).
- ⬜ Not done this phase (explicitly out of scope per the phase brief):
  daily/recurring engagement mechanics, AI image generation, social
  feed, chat, OAuth.

## Phase 11 — MeowVerse Similarity Engine: Visual Embeddings & Cat Discovery ✅
- ✅ Real embedding pipeline — ImageNet-pretrained MobileNetV3-Small
  (not the project's own breed-fine-tuned weights, and not a new model
  trained from scratch), 576-dim, L2-normalized, deterministic
  preprocessing. See ARCHITECTURE.md §19.
- ✅ Layered abstraction exactly as specified: `EmbeddingModel` →
  `CatEmbeddingService` → `VectorIndex` → `SimilarityService` → API →
  frontend — each layer swappable without touching the ones above it.
- ✅ `FAISSVectorIndex` (`IndexIDMap2` + `IndexFlatIP`, exact cosine
  similarity via inner product on normalized vectors) — persisted,
  survives a restart, reload verified, dimension-mismatch and
  corrupt-file detection verified.
- ✅ Content-hash deduplication — identical image bytes reuse one FAISS
  vector across multiple analyses rather than adding duplicates.
- ✅ Privacy: every candidate re-checked (public OR caller-owned) at
  the `SimilarityService` layer before it can reach a response; guests
  see public cats only. See ARCHITECTURE.md §21.
- ✅ `GET /api/v1/analyses/{id}/similar` — self-exclusion, k capped at
  20, post-retrieval breed/rarity/favorite filters, honest
  `search_mode: "embedding" | "unavailable"` (never a fabricated
  result when the model/index isn't available).
- ✅ "Cats Like This 🐾" section (analyze results page, public
  `/cat/[id]`, `/collection/[id]`) — real similarity percentages, a
  rotating cute loader, an honest "one of a kind" empty state driven
  by the actual result, and a small "How Similarity Works" explainer.
- ✅ `python -m app.cli.similarity_index {build,rebuild,verify}` —
  dev/admin-only, never HTTP-exposed; run for real against this
  project's own accumulated dev data (869 analyses backfilled, 980
  total rows verified with zero problems).
- ✅ Backend: 211/211 tests (was 170) including controlled-vector math
  tests (identical/orthogonal/ranked-distance vectors) per spec §28,
  not just HTTP-response tests. Frontend: 96/96 tests (was 85).
  Playwright E2E: 14/14 steps against real dev servers, zero console
  errors, real photos from the Oxford-IIIT Pet dataset already in this
  repo (not synthetic fixtures).
- ✅ Qualitative validation with real, non-cherry-picked photos (4
  breeds × 3 images) — reported honestly including the one query that
  didn't cluster with its own breed. See PROJECT_STATUS.md.
- 🐛 Two real bugs found and fixed this phase (not hypothetical): (1)
  torch and faiss-cpu both bundle their own OpenMP runtime, aborting
  the interpreter outright when both load in one process on Windows —
  fixed with the standard `KMP_DUPLICATE_LIB_OK=TRUE` workaround set
  in `app/__init__.py`. (2) `faiss.IndexIDMap` (the wrapper originally
  used) doesn't support `reconstruct()` at all — switched to
  `IndexIDMap2`, which maintains the reverse map needed for it.
- ⬜ pgvector — deliberately not introduced; the spec explicitly said
  not to unless existing infrastructure already required it, and it
  doesn't yet. `VectorIndex` is shaped so it's a future drop-in.
- ⬜ Formal retrieval benchmark (recall@K, etc.) — not performed; no
  reliable ground-truth similarity labels exist for this dataset (breed
  labels are not a similarity ground truth, and the spec explicitly
  warns against conflating the two). Documented honestly in
  PROJECT_STATUS.md rather than fabricated.

## Phase 12 — MeowVerse Explainable AI: Real Grad-CAM Breed Explanations ✅
- ✅ Real Grad-CAM (Selvaraju et al., 2017) implemented from scratch
  with PyTorch forward/backward hooks against the actual fine-tuned
  breed classifier's real weights — not the `pytorch-grad-cam` library
  pre-staged in `requirements-ml.txt` (deliberately not used, so every
  step stays auditable/testable), not a decorative or hard-coded
  heatmap. Target layer (`features[-1]`, a `(576,7,7)` feature map)
  verified by inspecting real tensor shapes, not assumed. See
  ARCHITECTURE.md §23.
- ✅ Confidence vs. Grad-CAM intensity kept strictly separate
  everywhere — schema, DB row, and UI.
- ✅ `breed_mode` honesty preserved: a demo-mode analysis always gets
  an honest `"unavailable"` explanation with a real reason, never a
  fabricated heatmap.
- ✅ `POST /api/v1/analyses/{id}/explanation` — on-demand only (never
  during analysis), ownership-enforced identically to every other
  analysis endpoint, cached on `(analysis_id, target_class,
  breed_model_version)` so a retrained classifier can never silently
  serve a stale explanation. See ARCHITECTURE.md §24.
- ✅ Real heatmap + alpha-blended overlay images, generated with OpenCV
  and stored through the existing `ImageStorageProvider` (extended
  with a new `load()` method to read the original photo back out —
  no second storage system).
- ✅ "Why MeowVerse thinks this is a [breed]" section on the analyze
  results page, public `/cat/[id]`, and `/collection/[id]` — a
  Original/AI Focus/Overlay switcher, a plain-language explanation, and
  an explicit "not proof, certainty, or a causal explanation" disclaimer.
- ✅ Backend: 246/246 tests (was 211) — including controlled Grad-CAM
  math tests (target layer, gradient capture, ReLU, normalization,
  determinism, and a real "different target class → different heatmap"
  gradient-dependence test per spec §23), ruff clean. Frontend: 106/106
  tests (was 96), lint/build clean.
- ✅ Playwright E2E (14 steps) against real dev servers with a real
  trained model and real Oxford-IIIT Pet photos — including cache
  reuse, cross-user denial, public-page access, mobile, and reduced
  motion, zero console errors.
- ✅ Real image qualitative validation across 5 breeds (British
  Shorthair, Siamese, Persian, Bengal, Sphynx) with real photos, not
  cherry-picked — including one real misprediction (a Bengal photo
  classified as Egyptian Mau at 61%) reported honestly rather than
  hidden. See PROJECT_STATUS.md.
- 🐛 Found and fixed two real pre-existing (Phase 8) hydration
  mismatches under `prefers-reduced-motion`, surfaced by this phase's
  own reduced-motion QA on the public `/cat/[id]` page — same root
  cause as Phase 10's `AuthCard` fix (a Framer Motion prop that
  disappeared entirely under reduced motion, changing what the server
  and a reduced-motion client each rendered): `useCardTilt`'s
  `style`/`handlers` and `CatCard`'s `whileTap`. Both fixed by keeping
  the prop structurally present always and only changing its *value*
  to a no-op under reduced motion.
- ✅ Optional faithfulness sanity check implemented (spec §27): masking
  the top 15% of each photo's heatmap and re-measuring confidence in
  the same target class showed a real mean drop of +0.558 across 5
  real photos (4 of 5 individually dropped meaningfully, one barely
  moved — reported honestly, not smoothed over). Explicitly documented
  as a sanity check, not proof of causality. See PROJECT_STATUS.md.

## Phase 13 — Creative Generation
- ⬜ `ImageGenerationProvider` interface + fallback UI
- ✅ Cat Card (image, name, breed, rarity, magic power, colors; download
     PNG, share, copy link) — built early, in Phase 8, as the "MAGICAL
     EXPERIENCE & CAT CARD" phase; still missing here: a QR code on the
     card, and an actual `mood` field/signal (neither exists yet — the
     Phase 8 card omits mood rather than fabricate it)
- ⬜ Wallpaper / avatar / sticker generation (the Cat Card already has a
     "Generate Wallpaper" placeholder button wired up and ready for this)

## Phase 14 — Testing
- ⬜ Backend: Pytest unit + integration + pipeline + API tests
- ⬜ Frontend: component tests
- ⬜ E2E: Playwright

## Phase 15 — Docker & CI/CD
- ⬜ Dockerfiles (frontend, backend), full Compose stack
- ⬜ GitHub Actions: lint, test, build gates

## Phase 16 — Documentation
- ⬜ Full README (features, architecture, setup, API, roadmap, etc.)

## Phase 17 — Final Polish
- ⬜ Accessibility pass, responsive pass, performance pass, security pass

---

## MVP Definition — reached as of Phase 9 ✅

Landing → upload → validate → detect/classify (real or explicit demo
mode) → fur color → AI profile → AI story → animated results page →
save + revisit history. Every item in that chain is real and verified
as of Phase 9: "save + revisit history" was the one outstanding piece
(Phase 8's "Save" only bookmarked locally, with no page to browse
those bookmarks) and Phase 9 delivered the real, authenticated version
— an account, a persistent per-user collection, and real history.
Similarity search, Grad-CAM, and (most) creative generation remain
explicitly post-MVP (Phases 11–13); collection/achievements got their
first pass alongside Phase 9 (since the spec bundled a basic persistent
collection into the same ask) and their full "Cat Universe" treatment
— gamification, XP/levels, breed discovery, the constellation map —
in Phase 10.

## Known Risks
- No Anthropic API key is configured on this dev machine — real
  profile generation (Phase 6) and story generation (Phase 7) have
  each been verified against the SDK's actual types/error hierarchy and
  via mocked tests (9 profile + 4 story), but not against a live
  Anthropic API call. `AnthropicLLMProvider` is real code implementing
  a well-documented, versioned API (SDK 0.121.0), not a guess — but the
  first live call should still be watched for anything the mocks
  couldn't catch (e.g. actual model output failing schema validation in
  a way the tests didn't anticipate — the retry-then-demo-fallback path
  exists exactly for this).
- Image generation (Phase 13) still depends on a provider abstraction
  with only a working `NullProvider` fallback — `ImageGenerationProvider`
  is still a null stub.
- Docker Desktop on Windows works for local dev but needs to be running
  before `docker compose up`; confirmed working in Phase 1. The backend
  Docker image still doesn't include `requirements-ml.txt` (Phase 4/5
  known gap, unchanged) — the `anthropic` SDK IS in the base
  `requirements.txt` though, so profile/story generation both work in
  Docker even though breed/color analysis doesn't.
- **Local dev Postgres runs on host port 5433, not 5432** (Phase 7) — a
  native Windows PostgreSQL service was already bound to 5432 on this
  machine, silently intercepting connections meant for the Docker
  container. `docker-compose.yml`, `.env`/`.env.example`, and
  `config.py`'s default all agree on 5433; CI's ephemeral Postgres
  container has no such conflict and stays on 5432 — see
  `.github/workflows/ci.yml`.
- Rate limiting is in-memory, single-process — now behind a
  `RateLimiter` protocol (Phase 9) specifically so a Redis-backed
  implementation is a drop-in swap for multi-instance production,
  which is still a follow-up, not done yet.
- **No password reset / email verification flow** (Phase 9) — accounts
  are created and authenticated, but there's no "forgot password"
  endpoint and no confirmation email is ever sent (no email-sending
  infrastructure exists at all yet). A user who forgets their password
  has no self-service recovery path today.
- **Local image storage doesn't survive a container rebuild** (Phase 9)
  — `LocalImageStorageProvider` writes to `backend/uploads/` on the
  local filesystem, gitignored and not part of any Docker volume
  mount. Real for local dev (the collection page genuinely shows the
  saved photo), but a production deployment needs the planned
  S3-compatible `ImageStorageProvider` implementation before photos
  can survive redeploys.
