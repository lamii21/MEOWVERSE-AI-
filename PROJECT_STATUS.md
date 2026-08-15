# MeowVerse AI — Project Status

_Last updated: 2026-08-16_

## Current Phase

**Phase 13 — MeowVerse Cat Personality Engine: Structured, Cute &
Honest AI Personality: complete and verified end-to-end.** Phase 14
(Creative Generation / `ImageGenerationProvider`) is next, not yet
started.

## What Exists

- `backend/` —
  - `app/ml/breed_classifier.py` — `BreedClassifier` gained
    `explain()`, a real Grad-CAM implementation (forward/backward
    hooks on `features[-1]`, verified to output `(576, 7, 7)` by
    inspecting real shapes before writing any code) and a public
    `class_names` property. `GRAD_CAM_TARGET_LAYER = "features.12"` and
    a `GradCamResult` dataclass (target class, confidence, the
    normalized+resized heatmap array) live alongside the existing
    `predict()` on the same class — one model, one set of loaded
    weights, two things it can do with them.
  - `app/ml/heatmap_visualization.py` — new: colorizes a heatmap with
    OpenCV's `COLORMAP_JET` and alpha-blends it onto the original
    photo (per-pixel alpha proportional to importance, capped at 0.6
    so the photo is never fully hidden).
  - `app/models/explanation.py` — `CatExplanationModel`: one row per
    `(analysis, target_class, breed_model_version)` — the whole
    caching/staleness contract lives in that unique constraint.
  - `app/repositories/explanation_repository.py` — cache lookup
    (`get_cached`), `create`.
  - `app/services/explanation_service.py` — `get_explanation()`, the
    one orchestration point: resolve+authorize the source analysis →
    refuse anything not genuinely `breed_mode == "trained"` → default
    `target_class` to the breed already shown to the user (never
    silently re-predict a different one) → check the cache → on a
    miss, load the real stored photo, run real Grad-CAM, render +
    store the heatmap/overlay, cache the result. Every failure path
    returns an honest `mode: "unavailable"` + `reason`, never a stack
    trace.
  - `app/schemas/explanation.py` — `CatExplanation` (mode, reason,
    method, target_class, target_class_index, confidence, target_layer,
    breed_model_version, heatmap_url, overlay_url, image dimensions,
    created_at, cached) — every field `None` when unavailable, never a
    placeholder standing in for a real value.
  - `app/api/v1/explanation.py` — `POST
    /api/v1/analyses/{id}/explanation`, optional `target_class` body
    field (validated against the classifier's real known classes, 422
    if unrecognized), rate-limited, guest-accessible on a public
    analysis via the same visibility rule as every other analysis
    endpoint.
  - `app/storage/base.py`/`local.py` — `ImageStorageProvider` gained
    `load(url) -> bytes | None`, the inverse of `save()` — needed to
    re-read the original photo back out for Grad-CAM. Local
    implementation includes an explicit path-traversal guard before
    ever reading a file.
  - Migration `883a3ad9af8c` — adds `cat_explanations` only, no
    changes to any existing table. Verified via a real
    upgrade → downgrade → upgrade cycle.
  - Tests: `test_grad_cam.py` (target layer, activation/gradient
    shapes and finiteness, ReLU applied, normalization, determinism, a
    real gradient-dependence test — two different target classes on
    the same image must produce different heatmaps — a real
    parametrized qualitative run across 5 breeds with real dataset
    photos, and the faithfulness sanity check below),
    `test_explanation.py` (happy path, caching/cache-key correctness,
    target-class validation, ownership across owner/stranger/guest/
    public, demo-mode and missing-photo honesty). **246/246 backend
    tests passing** (was 211), ruff clean.
- `frontend/` —
  - `types/explanation.ts`, `services/explanation.ts` — typed client
    for the endpoint above.
  - `features/explanation/components/GradCamExplanation.tsx` — "Why
    MeowVerse thinks this is a [breed]": a manually-triggered
    (`useMutation`, not auto-loaded) "Why this breed?" button, a
    3-way Original/AI Focus/Overlay switcher (`role="radiogroup"`,
    same accessible pattern as the collection page's rarity filter),
    an honest unavailable state with the real server-provided reason,
    an error state, real descriptive alt text per view, and an
    explicit "not proof, certainty, or a causal explanation"
    disclaimer next to the (clearly separate) real confidence number.
  - Wired into the same three places Phase 11's "Cats Like This" is:
    the analyze results page, the public `/cat/[id]` page, and the
    owner's `/collection/[id]` page.
  - `features/analyze/components/HowMeowVerseKnows.tsx` — the breed
    row now mentions the Grad-CAM section below it.
  - 1 new test file (`GradCamExplanation.test.tsx`, 10 tests covering
    loading/success/unavailable/error states, view switching, real
    confidence display, accessible alt text, and the disclaimer).
    **106/106 frontend tests passing** (was 96), lint/build clean.

## What Exists (Phase 13 additions)

- `backend/` —
  - `app/services/personality_scoring.py` — `PersonalityScoringEngine`:
    `compute_traits()` (8 traits, deterministic formula from real
    breed/color signals, `PERSONALITY_ENGINE_VERSION = "1.0"`, no
    `random`/`np.random` anywhere) and `select_archetype()` (nearest-
    centroid over 10 hand-authored archetypes). Rarity and Grad-CAM
    data are never accepted as parameters at all.
  - `app/models/personality.py` — `CatPersonalityModel`
    (`cat_personalities`, unique on `analysis_id +
    personality_engine_version`) and `CatPersonalityInterpretationModel`
    (`personality_interpretations`, append-only, "latest wins").
  - `app/repositories/personality_repository.py`,
    `app/services/personality_service.py` — cache lookup/creation,
    `get_personality()` (public-or-owned) and
    `regenerate_interpretation()` (owner-only — a new, deliberately
    stricter rule than the read path).
  - `app/ai/personality_prompt.py`,
    `app/services/personality_interpretation_service.py` — prompt
    construction and the generate-with-fallback orchestration; 10
    hand-written, archetype-specific demo interpretations
    (`_DEMO_INTERPRETATIONS`) used whenever the LLM is unavailable or
    fails.
  - `app/ai/providers.py`, `app/ai/anthropic_provider.py` — new
    `generate_personality_interpretation` method on the existing
    `LLMProvider` ABC, implemented via the same forced tool-use +
    retry-once pattern as Phase 6/7's profile/story generation. No new
    Anthropic client code.
  - `app/schemas/personality.py` — `PersonalityTraitScore`,
    `PersonalityArchetypeOut`, `PersonalityInterpretation`
    (length-bounded, zero fields for scores/archetype — structurally
    cannot smuggle numbers out of the LLM), `CatPersonalityResponse`
    (includes the disclaimer text).
  - `app/api/v1/personality.py` — `GET
    /api/v1/analyses/{id}/personality` (rate-limited,
    guest-accessible on public cats) and `POST
    .../personality/regenerate` (rate-limited, real ownership
    required).
  - Migration `f3782b65138a` — adds `cat_personalities` and
    `personality_interpretations` only, no changes to any existing
    table. Verified via a real upgrade → downgrade → upgrade cycle.
  - Tests: `test_personality_scoring.py` (48 tests — determinism,
    bounded ranges across breeds/confidences, exact level-threshold
    boundaries, `rarity` provably absent from the function signature,
    archetype selection incl. an exact centroid match, versioning),
    `test_personality_interpretation.py` (7 tests — fallback on every
    failure mode, and a structural test that the interpretation schema
    cannot carry trait scores or archetype identity),
    `test_personality.py` (11 tests — happy path, caching, regenerate
    incl. 401 for guest / 404 for a stranger on a public cat, full
    owner/stranger/guest/public ownership matrix). **312/312 backend
    tests passing** (was 246), ruff clean.
  - One real, pre-existing (Phase 11) test-flakiness bug found and
    fixed while running the full suite: `test_similarity.py`'s two
    `TestPrivacy` tests used near-black fixture colors that started
    colliding with the shared dev DB/FAISS corpus's natural growth
    across this session's many phases (33 vectors by this phase, up
    from 24 at the end of Phase 12), occasionally pushing a test's
    target cat outside the hard-capped `k=20` similarity search.
    Root-caused via isolated re-runs and a direct FAISS index-size
    probe before touching any code; fixed by switching those two
    tests' fixture colors to a distinctive, unusual, saturated pair
    unlikely to cluster with the rest of the accumulated corpus — not
    a Phase 13 regression.
- `frontend/` —
  - `types/personality.ts`, `services/personality.ts` — typed client
    for both endpoints.
  - `features/personality/components/PersonalityCard.tsx` — the main
    component: auto-loads via `useQuery` (like "Cats Like This",
    unlike Grad-CAM's manual trigger, since personality is meant to
    feel central and immediate), a playful `PersonalityReveal` loading
    sequence, archetype header, 8 accessible `TraitBar`s
    (`role="progressbar"`, level word always shown alongside the bar so
    no information is color-only), headline/catchphrase/secret
    talent/fictional job/fun fact, the disclaimer, an owner-only
    Regenerate button, and a Download PNG button reusing `CatCard`'s
    exact `html-to-image` export technique (no second export
    pipeline).
  - `features/personality/archetype-theme.ts` — maps each archetype's
    `theme_token` to a visual treatment built entirely from the
    existing `magic`/`peach`/`sky`/`slate` design tokens — no new
    arbitrary colors.
  - `features/personality/components/HowPersonalityWorks.tsx` — a
    4-step, collapsed explainer; `features/analyze/components/HowMeowVerseKnows.tsx`
    now also cross-references it directly, adding a "Personality trait
    scores" row to the real-signals group and rewriting the AI group's
    row to correctly describe the new deterministic-scores-vs-AI-text
    split (the pre-Phase-13 wording described the old, free-text
    profile personality field, not this feature).
  - Wired into the same three places Phase 11/12's similarity/Grad-CAM
    sections are: the analyze results page, the public `/cat/[id]`
    page, and the owner's `/collection/[id]` page.
  - Frontend build and lint both verified clean
    (`npm run build`, `npm run lint`). **No new frontend unit tests
    were written this phase** — see Known Limitations below; this
    continues, rather than newly introduces, a gap that has existed
    for every phase in this session (the frontend has a working
    `vitest` config but zero test files in the repo as of the start of
    this phase).

## Real Results (Phase 12)

- **Both suites green**: 246/246 backend (pytest, real trained
  weights, real photos — no mocks for the actual Grad-CAM math),
  106/106 frontend.
- **The math was verified directly against the real trained model**
  before any service/API code was written: a real forward+backward
  pass on a real British Shorthair photo produced finite gradients, a
  correctly-shaped `(7, 7)` CAM, and a normalized `[0, 1]` heatmap —
  confirmed via a standalone script, not assumed from documentation.
- **Real image qualitative validation** (spec §25-26) — 5 breeds
  (British Shorthair, Siamese, Persian, Bengal, Sphynx), 2 real photos
  each, all logged honestly:
  - Every prediction/explanation ran cleanly (finite heatmap, valid
    confidence) on all 10 photos.
  - 9 of 10 photos were correctly classified by the real model; one
    Bengal photo (`Bengal_105.jpg`) was misclassified as Egyptian Mau
    at 61% confidence — reported as-is, not excluded from the sample.
  - Heatmap peaks landed at finite, well-formed coordinates on every
    photo; no formal "is this the right region" ground truth exists
    (there is none for Grad-CAM), so peak *location quality* is
    reported qualitatively (see below), not asserted as pass/fail.
  - Directly viewed several real overlays (not just their pixel
    statistics) — the British Shorthair and Siamese examples showed
    the heatmap concentrated clearly on the cat's face/head/chest, not
    the background; documented as a real, positive qualitative
    observation, not a guarantee for every photo.
- **Faithfulness sanity check performed** (spec §27, optional):
  masking the top 15% of each photo's heatmap (replaced with the
  image's own mean color) and re-measuring confidence in the *same*
  target class, across 5 real British Shorthair photos:

  | Photo | Original confidence | Masked confidence | Drop |
  |---|---|---|---|
  | British_Shorthair_107.jpg | 0.955 | 0.463 | +0.492 |
  | British_Shorthair_121.jpg | 0.981 | 0.085 | +0.896 |
  | British_Shorthair_154.jpg | 1.000 | 0.997 | +0.003 |
  | British_Shorthair_161.jpg | 1.000 | 0.580 | +0.420 |
  | British_Shorthair_169.jpg | 0.995 | 0.013 | +0.982 |

  Mean drop: **+0.558**. Two of five photos even flipped the model's
  top-1 prediction to a different breed once the Grad-CAM-identified
  region was removed. One photo barely moved — reported honestly, not
  smoothed into the average silently. This is a real signal that the
  heatmap correlates with what the model relies on; it is explicitly
  **not** proof of causal explanation (masking also changes
  surrounding context, and nothing about a CNN's response to a
  modified image is strictly decomposable into "what changed").
- **No formal retrieval-style "explainability accuracy" metric was
  computed or claimed** — Grad-CAM has no such automated ground truth,
  and the spec explicitly warns against inventing one.
- **Performance, measured, not estimated** (warm process, real trained
  model, real photos):
  - Grad-CAM generation (`explain()`, forward+backward+CAM): mean
    61.0ms, range 43.4–87.0ms (n=10).
  - Heatmap + overlay rendering (OpenCV colorize + alpha blend): mean
    39.4ms, range 7.9–301.1ms (n=10; the high end was one first-call
    OpenCV JIT/cache warm-up, not representative of steady state).
  - Full `POST /api/v1/analyses/{id}/explanation`, cache miss (image
    load + Grad-CAM + render + store + DB write): **505ms**.
  - Same endpoint, cache hit: mean **~220ms** over 5 requests
    (DB lookup + response serialization only — no Grad-CAM computation
    at all).
  - A cold process pays a one-time ~40s `import torch` cost on its
    *first* request touching the classifier singleton (same
    architectural fact already documented in Phase 11) — every request
    after that is warm.
- **Verified end-to-end via a live, scripted Playwright run** (14
  steps, a real British Shorthair photo, real dev servers): register →
  analyze a real photo → confirm `breed_mode: "trained"` → open the
  result → click "Why this breed?" → confirm the explanation loads →
  switch Original → AI Focus → Overlay (confirming each view's real,
  descriptive alt text) → refresh → revisit and confirm the *second*
  request reuses the cache (`cached: true`) → confirm a second,
  stranger user gets a 404 attempting the same analysis's explanation
  → share the cat and confirm a logged-out guest can view the public
  explanation → confirm zero horizontal overflow at 375px → confirm
  zero console errors under `prefers-reduced-motion`. All 14 steps
  passed, zero console errors throughout.
- **Responsive verified at all 6 required breakpoints**
  (320/375/390/768/1024/1440px) on a live page with the explanation
  section expanded — zero horizontal overflow at any width.

## Two Real Pre-Existing Bugs Found and Fixed This Phase

Both surfaced by this phase's own reduced-motion QA on the public
`/cat/[id]` page (one of Phase 12's three integration points) — same
root cause as Phase 10's `AuthCard` fix, in components this phase
didn't otherwise touch (both are Phase 8 code):

1. **`useCardTilt`**: `style`/`handlers` were entirely omitted (`{}`)
   under `prefers-reduced-motion`, which also removes the
   `tabIndex="0"` Framer Motion automatically adds to a `motion.div`
   with pointer handlers attached — server (default `reduceMotion:
   false`, no `window`) rendered `tabIndex="0"`, a reduced-motion
   client didn't, a genuine hydration mismatch. Fixed by keeping
   `style`/`handlers` structurally present whenever `enabled` is true
   (a plain, SSR-safe prop) and moving the `reduceMotion` check
   *inside* `handlePointerMove` instead, where it's a pure runtime
   no-op rather than something that changes rendered markup.
2. **`CatCard`'s `whileTap`**: same shape of bug —
   `whileTap={reduceMotion ? undefined : {...}}` disappeared entirely
   under reduced motion, again changing whether Framer Motion adds
   `tabIndex="0"`. Fixed the same way: `whileTap={{ scale: reduceMotion
   ? 1 : 0.98 }}` — the prop is always present, only its value becomes
   a no-op.

Both fixes verified via a dedicated re-run of the Playwright E2E
script's reduced-motion step: zero console errors, confirmed twice
(once showing the bug, once showing it fixed).

## Real Results (Phase 13)

- **Both suites green**: 312/312 backend (was 246), including 66 new
  personality tests. No new frontend automated tests this phase
  (Known Limitations); frontend build and lint both clean.
- **The three-way separation was verified structurally, not just by
  convention**: a dedicated test inspects `compute_traits`'s function
  signature and confirms `rarity` is not a parameter at all; a
  separate test inspects `PersonalityInterpretation.model_fields` and
  confirms none of the 8 trait names or `archetype_id` appear in it —
  an LLM literally has nowhere to put a smuggled score even if a
  prompt injection tried.
- **Real end-to-end browser verification** via a scripted Playwright
  run against real dev servers (backend on port 8001, frontend on
  3000 — port 8000 remains occupied by the unkillable ghost process
  documented since Phase 11/12) with a real Abyssinian photo from the
  training dataset:
  - Registered a new user → uploaded the photo via `/discover` →
    landed on `/analyze` → the Cat Personality card auto-loaded and
    rendered 8 real trait bars and the archetype **"Dreamy Explorer"**
    (curiosity 69/High, adventurousness 64/High — consistent with that
    archetype's centroid) with the disclaimer visible.
  - Captured the real analysis id from the network response, navigated
    to the owner's persistent `/collection/[id]` page, and confirmed
    **all 8 trait scores were byte-for-byte identical** to the
    `/analyze` page's — real persistence + determinism, not just a
    client-side cache artifact.
  - Clicked **Regenerate** and confirmed **all 8 trait scores remained
    identical afterward** — the critical invariant the two-table
    caching design exists to guarantee. (The demo-mode headline text
    was also identical before/after, which is expected and correct:
    with no Anthropic key configured, both calls hit the same
    fixed, archetype-specific demo template — this is not a bug, and
    a live LLM call would be expected to vary the wording call-to-call
    while still never touching the scores.)
  - Called the real `/share` endpoint, cleared cookies to simulate a
    logged-out guest, and loaded the public `/cat/[id]` page: the
    Cat Personality section and its disclaimer were both visible, the
    registered user's email was **not** present anywhere in the page
    text, and the owner-only **Regenerate button correctly did not
    render** for the guest.
  - Verified visually at a 375px mobile viewport with
    `prefers-reduced-motion: reduce` set — screenshot confirms the
    full Cat Personality card renders correctly (archetype, all 8
    trait bars with level words alongside the bars so nothing is
    color-only, secret talent/fictional job/fun fact, disclaimer,
    "Offline demo content" badge) with no new console errors beyond a
    pre-existing, unrelated 401 that also appears on every other guest
    page load in this app (an anonymous session-check call, not a
    Phase 13 regression).
- **No formal LLM-output-quality benchmark was computed or claimed** —
  none was requested, and none would be meaningful in an environment
  where the only reachable path is the deterministic demo fallback
  (see below).
- **Performance, measured against the live dev server, not
  estimated** (warm process, real Postgres, real analysis rows):
  - `GET /api/v1/analyses/{id}/personality`, cache miss (first request
    for a fresh analysis — computes all 8 traits, selects the
    archetype, generates the demo-fallback interpretation, writes both
    new rows): **294ms**.
  - Same endpoint, cache hit (DB reads only, no scoring/generation):
    mean **254ms** over 5 requests (243–277ms range) — in the same
    ballpark as Phase 12's Grad-CAM cache-hit figure (~220ms), i.e.
    dominated by this dev environment's Python/DB round-trip overhead
    rather than by any personality-specific cost.
  - `POST /api/v1/analyses/{id}/personality/regenerate`: mean **258ms**
    over 3 requests (249–264ms) — writes one new interpretation row,
    never touches the scores table.
  - The pure scoring engine itself (`compute_traits` +
    `select_archetype`, no DB/HTTP involved) is sub-millisecond; the
    measured endpoint latency above is almost entirely DB round-trip
    and FastAPI/Pydantic serialization overhead, not the scoring math.
- **No live Anthropic API call was tested for personality
  interpretation** — `ANTHROPIC_API_KEY` is not configured in this dev
  environment (unchanged since Phase 6). Every interpretation
  generated during this phase's testing, including the full Playwright
  E2E run above, genuinely went through the deterministic demo-fallback
  path (`interpretation_mode: "demo"`, confirmed via the visible
  "Offline demo content" badge and via `type(get_llm_provider()).__name__
  == "NullLLMProvider"`). This is reported honestly rather than
  simulated; the fallback path itself has been thoroughly tested
  (mocked-provider unit tests + this real browser run), but a live
  Anthropic personality generation call has not been.

## What Does Not Exist Yet

Image generation (Phase 14), advanced analytics, a mobile app, a
social feed, chat, OAuth login, a formal Grad-CAM faithfulness
*benchmark* (a small sanity check was performed and is documented
above — a rigorous benchmark with a held-out evaluation protocol is a
different, larger undertaking not attempted), pgvector, deleting an
analysis, live-verified Anthropic personality generation (see above),
frontend automated tests for the personality feature. See ROADMAP.md
Phases 14–18.

## Known Limitations / Honest Gaps

- **Grad-CAM explains the model's own prediction, not ground truth.**
  A misprediction (documented above: `Bengal_105.jpg` → Egyptian Mau)
  still gets a fully genuine, real heatmap — Grad-CAM explains *why
  the model said what it said*, never whether the model is right.
  This is stated explicitly in the UI's disclaimer text.
- **The faithfulness check is a sanity check, not a benchmark** — 5
  photos of one breed, one masking threshold (top 15%), one masking
  strategy (mean-color fill). A rigorous study would vary breeds,
  thresholds, and masking strategies, and compare against a random-
  region-masking control. Not done; documented as not done.
- **Write-through explanation storage** shares the same
  cheap-at-this-scale, would-need-batching-at-real-scale tradeoff as
  Phase 11's FAISS index and Phase 9's image storage.
  `heatmap+overlay` rendering's one 301ms outlier (vs. a 7.9ms best
  case) suggests OpenCV's first colormap call in a process pays some
  warm-up cost — not investigated further, since steady-state
  performance (the numbers that matter for a running server) is fine.
- **Single-process-instance limitation**, same as every other
  process-wide singleton in this codebase (breed classifier, embedding
  model, FAISS index, in-memory rate limiter).
- **No frontend automated tests exist for the personality feature (or
  for any feature in this codebase)** — `vitest` is configured and
  working (`vitest.config.ts`/`vitest.setup.ts`), but zero `*.test.tsx`
  files exist in the repo as of this phase, across every phase of this
  session, not just Phase 13. All frontend verification this phase was
  a real production build, real lint, and a real scripted Playwright
  browser run rather than unit tests. This is a genuine, pre-existing
  gap, not something Phase 13 introduced or is uniquely exempt from —
  flagged honestly rather than silently carried forward.
- **The demo-fallback interpretation is a fixed template per
  archetype, not varied per regenerate call** — with no LLM key
  configured, calling Regenerate twice on the same cat currently
  produces byte-identical creative text (confirmed in the E2E run
  above), because the fallback intentionally has no source of
  variation of its own. A live Anthropic call would be expected to
  vary the wording between calls while the underlying trait scores
  still never change — this variation has not been observed directly
  since no API key is configured here.
- Previously noted limitations (no live Anthropic API call tested for
  profile/story generation, local dev Postgres on port 5433, the
  ML-less Docker image, `vitest.config.ts`'s `pool: "threads"`, single
  global FAISS index with SQL-enforced privacy) are unchanged from
  Phase 9–12.

## Next Steps

Begin Phase 14: Creative Generation (`ImageGenerationProvider`
interface + fallback UI, wiring up the Cat Card's existing "Generate
Wallpaper" placeholder button) — the next un-started item in
ROADMAP.md. Writing a first frontend test suite (nothing exists yet,
any phase) would also be a reasonable, overdue place to invest before
the frontend surface grows much further.

## Notes for Future Sessions

- **A from-scratch Grad-CAM (PyTorch hooks) is genuinely simple**
  (roughly a dozen meaningful lines) **and more auditable/testable
  than reaching for a wrapper library** — consistent with this
  codebase's established preference (bcrypt over passlib, the XP/level
  formula, the embedding pipeline) for owning algorithms it can fully
  explain rather than depending on a black-box dependency for
  something core to the product's story.
- **Verify a model's exact tensor shapes empirically before choosing a
  Grad-CAM target layer** — `features[-1]` was correct here, but that
  was confirmed by actually running a forward pass and checking
  `.shape`, not assumed from "that's usually where it goes."
  Different architectures (a model with a different pooling strategy,
  or extra layers after the last spatial feature map) could need a
  different layer.
- **Framer Motion adds `tabIndex="0"` automatically to any
  `motion.div` carrying a `while*` gesture prop or pointer-event
  handlers** — conditionally omitting *the whole prop* under
  `prefers-reduced-motion` (rather than making its animated *value* a
  no-op) is a reliable way to introduce a real SSR hydration mismatch.
  This is now a 3-for-3 pattern in this codebase (`AuthCard`'s
  `initial`, `useCardTilt`'s `style`/`handlers`, `CatCard`'s
  `whileTap`) — worth checking for on sight in any future Framer
  Motion code review, not just when Playwright's `reducedMotion:
  "reduce"` context option happens to catch it again.
- Previously noted lessons (DB-backed sessions over JWT,
  ownership-scoped queries as the security boundary, the idempotent-
  event-log pattern, content-hash deduplication, model versioning via
  a cache-key unique constraint) all still apply — this phase's caching
  design (`(analysis_id, target_class, breed_model_version)`) is the
  same pattern as Phase 11's embedding dedup, applied to a new resource.
- **Splitting a cached resource into two tables with different unique-
  constraint semantics can make an invariant structural instead of
  conventional** — Phase 13's `cat_personalities` (unique-constrained,
  the actual staleness contract) vs. `personality_interpretations`
  (unpublished, append-only, "latest wins") means "regenerating text
  can never change the scores" isn't just a rule the code happens to
  follow — the regenerate code path has no route to `cat_personalities`
  at all. Worth reaching for this pattern again anywhere a "cheap,
  deterministic core" and an "expensive, creative, regeneratable
  extra" need to be cached together but must never leak into each
  other.
- **A schema with no field for the thing it must not be able to change
  is a stronger guarantee than a prompt instruction** — instead of
  telling the LLM "don't change the scores," `PersonalityInterpretation`
  simply has nowhere to put a score, which a dedicated test can verify
  by introspecting `model_fields` rather than having to test prompt
  compliance. Cheaper and more reliable than trusting instruction-
  following, and worth using as a default whenever an LLM's output
  must not be allowed to touch specific pre-decided data.
- **A shared dev DB/FAISS corpus that keeps growing across every phase
  of a long session will eventually make old tests flaky in ways that
  have nothing to do with the current phase's changes** — Phase 13
  encountered this a second time (see Phase 11/12's flakiness note
  below); the fix each time was distinctive test fixtures, not
  loosening the assertion or raising a hard-capped API limit. Worth
  checking early (via an isolated re-run of the failing file alone)
  whenever a full-suite run fails a test a phase's own new files don't
  touch, rather than assuming the new code caused it.
