# MeowVerse AI — Project Status

_Last updated: 2026-08-16_

## Current Phase

**Phase 16 — AI/ML Validation, Benchmarking & Final Quality Assurance:
complete.** A validation/hardening pass, not a new feature phase — see
[AI_VALIDATION_REPORT.md](AI_VALIDATION_REPORT.md) for the full,
honest scorecard. Two real bugs were found and fixed this phase (fur
color non-determinism, an unsuppressed `openai` SDK logger), plus a
durable fix for a pre-existing, twice-recurring test-fixture pollution
issue in the similarity test suite. Phase 17 (Production Readiness) is
next, not yet started.

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
    (`npm run build`, `npm run lint`). **Correction, added after this
    entry was first written**: this phase originally, incorrectly,
    claimed no frontend test files existed anywhere in the repo. That
    was a research error — a real 22-file, 106-test `vitest` suite has
    existed since the initial commit, covering CatCard, Grad-CAM,
    auth, collection, gamification, similarity, and story components,
    and was passing throughout Phase 12. The actual, narrower gap:
    Phase 13 itself didn't add tests for its *own* two new components
    (`PersonalityCard`, `TraitBar`), breaking the pattern every other
    phase followed. Fixed retroactively — see Phase 14's entry below.

## What Exists (Phase 14 additions)

- `backend/` —
  - `app/ai/providers.py` — `ImageGenerationProvider` (a Phase-13-era
    scaffold) gained one new abstract method, `generate_portrait`, plus
    `ImageGenerationError` (a closed set of `PortraitErrorCode`s) and
    `PortraitGenerationResult`. `generate_wallpaper`/`generate_avatar`
    remain deliberately unimplemented — a separate, not-yet-built
    feature this phase doesn't repurpose.
  - `app/ai/openai_image_provider.py` — `OpenAIImageGenerationProvider`:
    real `gpt-image-1` image-conditioned generation via
    `images.edit(image=..., prompt=..., input_fidelity="high", ...)`,
    verified against the installed `openai` 3.1.0 SDK's actual method
    signature and exception hierarchy before writing any code (not
    assumed). `openai==3.1.0` added to `requirements.txt` and
    installed.
  - `app/ai/portrait_prompt.py` — the backend-only, deterministic
    `PortraitPromptBuilder` (`PROMPT_VERSION = "1.0"`): identity
    preservation (always present, never invents unobserved features),
    known-signals (breed/colors, only when real), style/environment/
    atmosphere (10 styles, rarity, optional Phase 13 archetype), and a
    sanitized, structurally-isolated optional user customization
    section.
  - `app/schemas/portrait.py` — `PortraitStyle` (10-value enum),
    `PORTRAIT_STYLE_LABELS`, `PortraitGenerateRequest` (style +
    ≤120-char customization + `force_new`), `PortraitOut` (incl.
    `reused`, `owned`, `gamification`).
  - `app/models/portrait.py` — `CatPortraitModel` (`cat_portraits`):
    no unique constraint (an explicit "Generate Again" must allow a
    real duplicate); a `generation_identity_hash` + composite index
    backs the soft dedup lookup instead.
  - `app/repositories/portrait_repository.py`,
    `app/services/portrait_service.py` — the full orchestration:
    resolve+authorize (owner-only, spec §9) → dedup lookup → build
    prompt → load the real original photo (never Grad-CAM, never the
    similarity embedding, never a previous portrait) → call the
    provider → re-validate the returned image (format/dimensions/size,
    never trusted blindly) → store → persist success or an honest
    failure (never silently discarded).
  - `app/api/v1/portrait.py` — `GET
    /api/v1/analyses/{id}/portraits`, `POST` (owner-only, its own
    stricter rate limit, CSRF-protected), `GET
    /api/v1/portraits/{id}`, `POST .../share`, `POST .../unshare`.
  - `app/core/rate_limit.py` — new `enforce_portrait_rate_limit`
    (default 5/min, own key prefix), reusing the existing
    `RateLimiter` abstraction.
  - `app/services/progression.py`, `achievement_definitions.py`,
    `collection_service.py` — `PORTRAIT_GENERATED` XP event (20,
    modest by design), two new achievements ("First Portrait," "Style
    Collector" — 5 distinct styles), backed by real
    `portrait_repository` count queries.
  - Migration `198e1f71f53e` — adds `cat_portraits` only, no changes
    to any existing table. Verified via a real upgrade → downgrade →
    upgrade cycle.
  - Tests: `test_portrait_prompt.py` (34 tests — determinism, identity
    signals, no-hallucination, style/personality/rarity separation,
    sanitization/prompt-injection resistance), `test_portrait_provider.py`
    (11 tests — every provider failure mode, dedup, force-new, failed-
    generation persistence, using a real DB row via the HTTP client
    plus a mocked provider), `test_portrait.py` (23 tests — the honest
    unavailable path against this environment's real, unconfigured
    provider; ownership; multiple portraits; sharing/privacy; email
    never leaked; gamification; the stricter rate limit's real 429 on
    the 6th request). **380/380 backend tests passing** (was 312),
    ruff clean.
- `frontend/` —
  - `types/portrait.ts`, `services/portrait.ts` — typed client;
    `PORTRAIT_STYLE_OPTIONS` mirrors the backend's style metadata
    (UI-facing only — the frontend never constructs prompt text).
  - `features/portrait/components/StyleSelector.tsx` — accessible
    10-style radiogroup, same pattern as Grad-CAM's view switcher and
    the collection page's rarity filter.
  - `features/portrait/components/PortraitReveal.tsx` — playful,
    indeterminate loading sequence (spec §18/§19: no fake percentages),
    reduced-motion aware.
  - `features/portrait/components/BeforeAfterViewer.tsx` — a simple
    Original/AI Portrait toggle (spec §31: "do not make the UI overly
    complicated" — a two-way switcher, not a drag slider).
  - `features/portrait/components/PortraitCard.tsx` — the collectible
    result card: always-visible "AI-generated artwork" label, reuses
    `CatCard`'s exact PNG export technique and the existing `/share`
    endpoint (no second export/share pipeline), Generate Again.
  - `features/portrait/components/PortraitStudio.tsx` — the
    orchestrator: auto-loads existing portraits (like "Cats Like
    This"), but generation itself is always a manually-triggered
    action (like Grad-CAM/Story) since a real provider call is
    expensive; maps every `PortraitErrorCode` to a distinct, friendly,
    honest message.
  - `app/portrait/[id]/page.tsx`,
    `features/portrait/components/PublicPortraitView.tsx` — the public
    share page; only shows cat-name/breed context when the *parent
    analysis* is independently public too (a shared portrait never
    implies its source cat is shared).
  - Wired into the same three places Phase 11-13's similarity/Grad-CAM/
    personality sections are: the analyze results page, the public
    `/cat/[id]` page, and the owner's `/collection/[id]` page.
  - 3 new test files (`StyleSelector.test.tsx`, `PortraitCard.test.tsx`,
    `PortraitStudio.test.tsx`, 26 tests) plus a 2-file, 18-test
    backfill for Phase 13's previously-untested components
    (`PersonalityCard.test.tsx`, `TraitBar.test.tsx`) — corrective work
    done at the very start of this phase, see "Notes for Future
    Sessions." **150/150 frontend tests passing** (was 106 at the true
    start of this phase), lint/build clean.

## What Exists (Phase 15 additions)

- `backend/` —
  - `app/schemas/explore.py` — `DiscoveryCatOut` (deliberately not a
    reused `AnalysisResult` — no owner fields to accidentally leak),
    `ExploreCatsPage`, `FeaturedCatsResponse`, `BreedExplorerOut`,
    `PersonalityArchetypeExplorerOut` (carries its own non-scientific
    disclaimer), `ColorExplorerOut`, `ExploreSort`.
  - `app/repositories/analysis_repository.py` — `list_public_analyses`
    (SQL-paginated), `list_public_analyses_unpaginated` (the archetype/
    color Python-filtering path's input), `get_public_breed_counts`,
    `get_distinct_breeds_explored`/`get_distinct_colors_explored`
    (join `collection_events` back to `cat_analyses`). No new table —
    every function reads existing columns.
  - `app/repositories/story_repository.py`,
    `portrait_repository.py` — new `get_analysis_ids_with_public_stories`/
    `get_analysis_ids_with_public_portraits`, batched (one query for
    a whole page, not one per cat), scoped to `is_public` specifically
    (distinct from the owner-facing versions Phase 10/14 already had).
  - `app/services/explore_service.py` — the listing/filtering/sorting
    orchestration, the deterministic featured-selection formula, and
    the breed/personality/color explorer aggregation. Archetype
    computed in-process via Phase 13's `compute_traits`/
    `select_archetype` — zero extra queries, never a join against
    `cat_personalities`.
  - `app/api/v1/explore.py` — `GET /api/v1/explore/{cats,featured,
    breeds,personalities,colors}`, all guest-accessible, all behind a
    new, deliberately looser rate limit (see below).
  - `app/api/v1/analyses.py` — `get_cat` now grants a `CAT_EXPLORED`
    gamification event when a signed-in visitor opens a public cat
    they don't own.
  - `app/core/rate_limit.py`, `app/core/config.py` — new
    `enforce_explore_rate_limit` (120/min, own key prefix) — see "Real
    Results" below for why this was added mid-phase, not planned from
    the start.
  - `app/services/progression.py`, `achievement_definitions.py`,
    `collection_service.py` — `CAT_EXPLORED` XP event (10, idempotent
    per cat), four new achievements (First Explorer, Curious Whiskers,
    Breed Seeker, Color Hunter).
  - Migration `47eb5d38195f` — three new indexes on `cat_analyses`
    (`is_public` + `created_at`/`rarity`/`breed_label`), no table
    changes. Verified via a real upgrade → downgrade → upgrade cycle.
  - Tests: `test_explore_privacy.py` (10 tests — spec §39's mandatory
    regression suite: a private cat absent from every discovery
    surface, similarity search, and the public cat-detail endpoint),
    `test_explore.py` (27 tests — listing/pagination/search/filters/
    sort/featured-determinism/explorers, plus a live query-counting
    N+1 test), `test_explore_gamification.py` (9 tests — XP
    idempotency, all four achievements, revisits never inflate
    progress). **426/426 backend tests passing** (was 380), ruff clean.
- `frontend/` —
  - `types/explore.ts`, `services/explore.ts` — typed client for all
    five endpoints.
  - `features/explore/components/` — `DiscoveryCatCard` (same compact-
    tile shape as `CollectionCard`, reusing the exact rarity visual
    language, but built from `DiscoveryCatOut` so there's no owner
    field to leak), `DiscoverySearch`, `DiscoveryFilters` (rarity +
    has-story/has-portrait chips), `DiscoveryCatGrid` (loading
    skeleton/error/empty states, "Load more"), `FeaturedCats`,
    `DiscoveryBreedExplorer`, `DiscoveryPersonalityExplorer` (shows
    the non-scientific disclaimer), `DiscoveryColorExplorer`,
    `ExploreHero`.
  - `app/explore/page.tsx` — uses `useInfiniteQuery` (not a manual
    page/accumulated-state + `useEffect` combination, which an
    `eslint-plugin-react-hooks` rule correctly flagged as a real
    cascading-render anti-pattern during this phase's own build
    verification — fixed by switching to the library's idiomatic
    infinite-list primitive instead of suppressing the lint rule).
  - `features/auth/components/AppNavbar.tsx` — added an "Explore" nav
    link for both guest and signed-in users.
  - 9 new test files, 43 tests (`DiscoveryCatCard`, `DiscoverySearch`,
    `DiscoveryFilters`, `DiscoveryCatGrid`, `FeaturedCats`,
    `DiscoveryBreedExplorer`, `DiscoveryPersonalityExplorer`,
    `DiscoveryColorExplorer`, and a page-level integration test).
    **193/193 frontend tests passing** (was 150), lint/build clean.

## What Exists (Phase 16 additions)

Phase 16 was explicitly a validation/hardening pass, not a feature
phase (spec §33: "do not overengineer") — its additions are
evaluation tooling and two real bug fixes, not new product surface.

- `backend/ml/evaluation/phase16_validate.py` — extends the existing
  `evaluate.py` with top-1/top-3 accuracy, confidence-calibration
  buckets, high-confidence-wrong-prediction detection, confusion
  matrix analysis (strongest/weakest classes, top confusion pairs),
  and a rendered `confusion_matrix.png`. Writes
  `ml/evaluation/classification_results.json`.
- `backend/ml/evaluation/phase16_robustness.py` — runs the real
  production pipeline (`_load_and_validate_image` →
  `BreedClassifier.predict` → `FurColorAnalyzer.predict`) against real
  non-cat photos (person, dog ×2, landscape, flower) and 13 synthetic
  image edge cases (tiny/huge/extreme-aspect-ratio/grayscale/RGBA/
  corrupted/empty/low-light/overexposed/partially-cropped), honestly
  marking the 2 cases with no real available test image (multi-cat
  frames, extreme far/close framing) as `NOT VERIFIED` rather than
  simulating them. Writes `ml/evaluation/robustness_results.json`.
- `ml/evaluation/dataset_report.json` — real dataset statistics plus a
  direct, this-phase filename-overlap check across train/val/test
  (zero found).
- `ml/evaluation/benchmark_results.json` — consolidated real latency
  measurements for the similarity engine and a live Grad-CAM sanity
  check, each clearly labeled with sample size and whether it was
  re-measured this phase or is historical.
- **Real bug #1 — fur color non-determinism, found and fixed**:
  `app/ml/fur_color.py`'s `cv2.grabCut` call had no RNG seed (only the
  downstream `KMeans` did), so repeated calls on byte-identical input
  produced different foreground masks and therefore different color
  swatches. Fixed with `cv2.setRNGSeed(42)`; a regression test
  (`test_predict_is_deterministic_on_a_real_photo_across_repeated_calls`)
  was added to `tests/test_fur_color.py`.
- **Real bug #2 — an unsuppressed third-party SDK logger, found and
  fixed**: `app/core/logging.py` suppressed `anthropic`'s logger to
  `WARNING` but never added `openai`'s (added in Phase 14) — a
  separate logger namespace, so with this app's `debug=True` default
  it would have inherited `DEBUG` and could log request/response
  detail. Fixed by adding the same suppression; a new test file
  (`tests/test_logging_config.py`) was added.
- **A pre-existing, twice-recurring test-fixture bug, durably fixed**:
  `test_similarity.py::TestPrivacy`'s two tests had already been
  "fixed" once in Phase 13 (a more "distinctive" hardcoded color) and
  failed again this phase for the same underlying reason — a
  hardcoded fixture color is never actually run-unique, and Phase 11's
  content-hash embedding dedup is global and permanent, so *every*
  previous local regression run silently left behind another analysis
  row sharing the same vector (52 found sharing one `vector_id` by
  direct measurement). Fixed durably this time: the two uploads within
  one test run now share byte-identical content (a guaranteed,
  unbeatable 1.0 similarity score) generated fresh from `uuid4` on
  every run (so this run's fixture can never collide with any other
  run's, past or future) — see `tests/test_similarity.py`'s
  `_unique_color()` docstring for the full, measured diagnosis.
- **AI_VALIDATION_REPORT.md** — the full scorecard, dataset/model/
  robustness/security/privacy findings, and an honest VERIFIED /
  PARTIALLY VERIFIED / NOT VERIFIED claims summary. See that file for
  everything this phase found — not duplicated here in full.
- Backend: **429/429 tests passing** (was 426 — 2 new test files plus
  1 extended one), ruff clean. Frontend: unchanged this phase (no
  frontend code touched), re-confirmed still 193/193 passing.

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
  personality tests. This phase originally shipped without tests for
  its own new frontend components — backfilled in Phase 14
  (`PersonalityCard.test.tsx`, `TraitBar.test.tsx`) against the
  existing, already-106-test-strong `vitest` suite; frontend build and
  lint both clean.
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

## Real Results (Phase 14)

- **Both suites green**: 380/380 backend (was 312, including 68 new
  portrait tests), 150/150 frontend (was 124, including this phase's
  own 26 new tests plus the 18-test Phase 13 backfill). Ruff/lint/build
  all clean.
- **A real provider implementation, verified against the real SDK,
  never exercised live in this environment**: `OpenAIImageGenerationProvider`
  is genuine code against `openai` 3.1.0's actual, introspected
  `images.edit` signature and exception hierarchy — but no
  `IMAGE_GENERATION_API_KEY`/`OPENAI_API_KEY` is configured on this dev
  machine (same honest gap as Anthropic since Phase 6), so a live
  `gpt-image-1` call was never performed. Every "succeeded" code
  path — storage, output re-validation, sharing, multiple portraits,
  download, the public page, gamification, dedup/"Generate Again" — was
  instead verified via 11 mocked-provider backend tests and mocked
  frontend component tests, which is a real and appropriate way to
  verify that code without a key, but is explicitly **not** the same
  as a live end-to-end image having been produced.
- **The one thing that *was* verified fully live, end to end**: the
  honest "no provider configured" path — via a real Playwright browser
  run (register → analyze a real Bengal photo → open Portrait Studio →
  select Cosmic, type a custom idea → Generate) the app's real backend
  genuinely returned `status: "failed"`, `error_code:
  "provider_unavailable"`, and the UI rendered the exact honest
  message ("Portrait generation is currently unavailable — no
  image-generation provider is configured in this environment.") —
  never a fake or placeholder image. The rest of the page (Cat
  Personality, Grad-CAM) kept rendering normally alongside it,
  confirming the unavailable state doesn't break anything else.
  Verified again at a 375px mobile viewport with
  `prefers-reduced-motion: reduce`, zero new console errors.
- **Performance, measured against the live dev server for every code
  path this environment can actually reach** (warm process, real
  Postgres, real analysis row):
  - `POST /api/v1/analyses/{id}/portraits`, the honest unavailable
    fast-fail path (pending row inserted, immediately marked failed,
    two real DB writes): mean **268ms** over 5 requests (250–290ms).
  - `GET /api/v1/analyses/{id}/portraits` (list): mean **237ms** over
    3 requests.
  - The 6th generation request within a minute genuinely returned
    **HTTP 429** — the stricter, portrait-specific rate limit (5/min)
    confirmed live, not just in a unit test.
  - Pure prompt-building latency (`build_prompt()`, no I/O): mean
    **0.0099ms**, max 0.2486ms over 1000 calls — confirms the
    ~250-290ms endpoint latency above is entirely DB/HTTP overhead in
    this dev environment, not the prompt construction itself.
  - **Real `gpt-image-1` provider generation latency was not measured**
    — there is no live call to time. Not fabricated; reported as
    unmeasured.

## Real Results (Phase 15)

- **Both suites green**: 426/426 backend (was 380, including 46 new
  discovery tests), 193/193 frontend (was 150, including 43 new
  discovery tests). Ruff/lint/build all clean.
- **A real bug found and fixed via live E2E, not caught by any unit
  test**: a single `/explore` page load fires 5 parallel section
  requests, and the general `enforce_rate_limit` (20/min, sized for
  AI-cost-bearing endpoints) tripped false-positive `429`s during
  completely ordinary browsing — confirmed live via a Playwright
  browser run mid-development (a console log full of `429` errors and
  an empty discovery grid). Fixed with a new, deliberately looser
  `enforce_explore_rate_limit` (120/min, same `RateLimiter`
  abstraction, own key prefix) — re-verified with a clean E2E re-run
  afterward. Documented here per this phase's own instruction: "if you
  discover a real bug while testing, fix it before declaring the phase
  complete."
- **Privacy regression suite (spec §39, mandatory) — all 10 tests
  pass**: a private cat is confirmed absent from `/explore/cats`,
  `/explore/featured`, every Explorer's examples, and similarity
  search results; a stranger's similarity request against a private
  source cat 404s; no email/user_id ever appears in any discovery
  response.
- **N+1 prevented and measured, not assumed**: a direct, instrumented
  measurement (a real SQLAlchemy `before_cursor_execute` listener
  against the live dev database) confirmed the main `/explore/cats`
  listing fetches 24 public cats — out of 538 real, accumulated public
  cats in this dev database — in **exactly 4 SQL queries** (count +
  select + 2 batched public-story/public-portrait existence checks),
  independently confirmed by a dedicated pytest query-counting test.
  This stays flat regardless of page size or result count.
- **Real, live browser E2E (27 steps)** against real dev servers with
  a real Ragdoll photo and two real users: register → analyze → share
  → logout → browse `/explore` as a guest against 538 real
  accumulated public cats → search "Ragdoll" → filter by breed via
  Breed Explorer → filter by personality via Personality Explorer →
  open a public cat (both the Personality and "Cats Like This"
  sections rendered, zero unexpected console errors) → register a
  second user, create a private (never-shared) cat → confirmed it's
  absent from `/explore` and that its direct public-page URL returns a
  real `404` → verified visually at a 375px mobile viewport (screenshot
  confirms a fully populated, cute discovery page: hero, search,
  rarity/story/portrait chips, Featured Cats, Breed/Personality/Color
  Explorers with real counts, a 24-of-538 "Latest Discoveries" grid,
  and a working Load More button) → reduced motion → refresh
  persistence. All 27 steps passed. The single console message
  recorded during the run was an *expected* `404` — the deliberate
  navigation to the private cat's public URL to confirm it's blocked,
  not a real error.
- **Performance, measured against the live dev server, not
  estimated** (warm process, real Postgres, 538 real accumulated
  public cats):
  - `GET /api/v1/explore/cats` (default listing): cold 421ms, warm
    mean 252ms over 5 requests (227–263ms).
  - Same endpoint with a search term: mean 264ms over 3 requests.
  - Same endpoint with a rarity filter (pure SQL path): mean 245ms
    over 3 requests.
  - Same endpoint with an archetype filter (the Python-side,
    unpaginated-fetch-then-filter path): mean 315ms over 3 requests —
    measurably higher than the pure-SQL path, as expected, but still
    well within an interactive range at this dataset size (538 public
    cats).
  - `GET /api/v1/explore/featured`: mean 315ms over 3 requests.
  - `GET /api/v1/explore/breeds`: mean 325ms over 3 requests.
  - `GET /api/v1/explore/personalities`: mean 344ms over 3 requests.
  - `GET /api/v1/explore/colors`: mean 355ms over 3 requests.
  - `GET /api/v1/analyses/{id}/similar` (pre-existing Phase 11
    endpoint, sanity-checked at this phase's larger dataset size, not
    re-architected): cold **10.27s** (the same one-time `import torch`
    cost on the embedding model's first touch documented since Phase
    11 — not a Phase 15 regression), warm 567ms/747ms over 2
    subsequent requests.
  - Database query count for the main listing: **exactly 4**,
    confirmed both by instrumented measurement and a dedicated test —
    see above.

## Real Results (Phase 16)

- **The full scorecard, findings, and honest VERIFIED/NOT VERIFIED
  claims summary live in [AI_VALIDATION_REPORT.md](AI_VALIDATION_REPORT.md)**
  — this section intentionally doesn't duplicate it in full.
- **Breed classifier re-evaluated, not just cited**: re-running the
  real evaluation script this phase produced byte-identical accuracy
  (87.50% top-1) to the previously stored report, confirming full
  reproducibility. New this phase: top-3 accuracy (**98.61%**), and a
  direct confidence-calibration pass that found **16 of 360 test
  predictions (4.4%) were confidently (≥80%) wrong** — a real,
  previously-unmeasured finding, surfaced honestly rather than
  smoothed into an aggregate accuracy number.
- **The most important finding in this phase**: MeowVerse's breed
  classifier has no cat/non-cat gate. Tested directly against 5 real
  non-cat photos — a real photo of a dog was classified "Abyssinian"
  at **94.52% confidence**. Evaluated and documented, per this phase's
  explicit instruction *not* to add a new model to fix it — a
  cat/non-cat gate is proposed as a scoped future phase, not built
  here.
- **Zero crashes across 18 real edge-case/non-cat inputs** — including
  a 4000×4000 image, extreme aspect ratios, grayscale, RGBA, a
  truncated JPEG, and empty bytes. 4 were correctly rejected by
  existing input validation; 14 processed without error.
- **A real, previously-undocumented non-determinism bug was found and
  fixed**: the fur-color pipeline's GrabCut segmentation step had no
  RNG seed, producing different results across repeated calls on
  identical input — direct measurement showed 5 calls produce 3
  distinct outputs before the fix, 1 identical output after it.
- **A real logging/secret-exposure gap was found and fixed**: the
  `openai` SDK's logger (added in Phase 14) was never added to the
  existing third-party-logger suppression list `anthropic` already
  had — fixed to match.
- **A pre-existing, twice-recurring test flakiness bug was root-caused
  and durably fixed** (not just patched a third time) — see "What
  Exists (Phase 16 additions)" above for the full diagnosis.
- **Both LLM/image-generation providers remain honestly `NOT VERIFIED
  LIVE`** — confirmed directly this phase via `get_llm_provider()`/
  `get_image_generation_provider()`, both resolving to their Null
  fallback, no key configured for either.
- **Regression**: 429/429 backend tests passing (was 426), ruff clean.
  Frontend untouched, re-confirmed 193/193 passing.
- **Full-stack regression re-confirmed fresh this phase, not reused
  from Phase 15**: 429/429 backend (`pytest`), ruff clean, 193/193
  frontend (`vitest`), `eslint` clean, `next build` production build
  clean — every one of these was actually re-run this phase, not
  assumed from a prior phase's numbers.
- **Live browser E2E** against real `uvicorn`/`next dev` servers,
  scripted with Playwright (no project Playwright config existed yet,
  so a standalone script was used, same pattern as every prior phase's
  E2E): guest landing → upload a real Persian photo → analysis with a
  real breed/confidence/fur-color result → Grad-CAM ("Why this
  breed?") → personality card → story generation → Portrait Studio →
  guest Save prompt → register → re-analyze while authenticated →
  Collection ("My Cat Universe," real stats) → Explore → search →
  breed filter → logout → login → **collection persists after
  re-login** → a second, unshared analysis confirmed **404 to a
  stranger** (private isolation) → mobile viewport (375px) → reduced
  motion. Zero unexpected console errors — the only console/network
  entries were the architecturally-expected guest `/me` 401 (Phase 9)
  and correct owner-only 404s for an unclaimed guest analysis.
  A separate, isolated follow-up script specifically re-verified the
  Collection → detail-page → Favorite/Share flow (the one step the
  main run's screenshot caught mid-hydration, before the buttons had
  rendered): confirmed the `/collection/[id]` navigation and both
  buttons render correctly once given time to settle after a
  client-side route change — a test-script timing gap, not a product
  bug, and not glossed over rather than reported honestly here.

## What Does Not Exist Yet

Advanced analytics, a mobile app, comments, direct messages, a
follower system, chat, notifications, a public "like" mechanism (spec
§21 deliberately steered away from this — "Save to My Collection"
already exists and is preferred), OAuth login, a formal Grad-CAM
faithfulness *benchmark* (a small sanity check was performed and is
documented above — a rigorous benchmark with a held-out evaluation
protocol is a different, larger undertaking not attempted), pgvector,
deleting an analysis, live-verified Anthropic personality generation
(see above), live-verified `gpt-image-1` portrait generation (see
above), wallpaper/avatar/sticker generation (a distinct, still-unbuilt
feature — the Cat Card's "Generate Wallpaper" button remains an
honest disabled placeholder), an "N portraits" badge on the collection
grid card (a Phase 14 scope trim, unchanged), Open Graph social-preview
metadata for public discovery pages (spec §23 — not implemented this
phase; see Known Limitations). See ROADMAP.md Phases 16–19.

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
- **Corrected (previously wrong) claim**: this section originally said
  no frontend automated tests existed anywhere in the codebase. That
  was a research error — 22 test files / 106 passing tests already
  existed (since the initial commit) covering many earlier phases'
  components. The real, narrower gap this phase left behind: no tests
  were written for Phase 13's own two new components. Backfilled in
  Phase 14 (`PersonalityCard.test.tsx`, `TraitBar.test.tsx`, 18 tests) —
  see Phase 14's entry.
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
- **No live `gpt-image-1` call has been performed** — same honest gap
  as Anthropic, now applying to the image-generation provider too. The
  provider code is real and verified against the SDK's actual surface,
  covered by 11 mocked-failure-mode tests, but the first live call
  should still be watched for anything the mocks couldn't catch (e.g.
  a real response shape the mocks didn't anticipate).
- **The public `/portrait/[id]` page doesn't show the Phase 13
  personality archetype**, even when both the portrait and the
  personality are public — a deliberate scope decision (matching
  `/story/[id]`'s similarly narrow, single-purpose share page rather
  than cross-embedding every other feature), not an oversight. Could
  be added later with one more public-safe fetch if wanted.
- **No "N portraits" badge on the collection grid card** — portraits
  are fully manageable from the owner's `/collection/[id]` detail page
  (where `PortraitStudio` is mounted, satisfying spec §36's "integrate
  into the Cat Collection, do not build a separate system"), but the
  grid/list view itself doesn't surface a portrait count. A scope trim
  for this phase's size, not a missing capability — the underlying
  batched-count repository query pattern already exists for stories
  and could be mirrored later.
- **"Save" is not a separate portrait action** — spec §32 listed
  Save/Download/Share/Generate Again, but unlike an anonymous/guest
  analysis, portrait generation always requires authentication already
  (spec §9), so every portrait is already persisted to the owner's
  account the moment it's created; a redundant "Save" button with
  nothing further to do would have been decorative, not functional, so
  it was intentionally omitted.
- **Archetype/color-filtered `/explore/cats` requests use a Python-side
  pagination path, not pure SQL** — measured at 315ms vs. ~250ms for
  the pure-SQL path at this dev database's current 538-public-cat
  scale (see "Real Results" above). Fine today; would need a real
  stored/indexed column (or a materialized view) for either field if
  the public cat count grew into the tens of thousands. Documented as
  a real, known tradeoff, not silently accepted.
- **`most_discovered` sort falls back to recency when combined with an
  archetype or color filter** — the SQL-side `CAT_EXPLORED`-count join
  only exists on the pure-SQL listing path; adding a second batched
  count query to the Python-side path for this one sort+filter
  combination was judged not worth the complexity at this project's
  scale. Documented in `explore_service._sort_key`'s own comment, not
  silently wrong.
- **No Open Graph / social-preview metadata was added to `/explore` or
  the discovery-enriched public pages this phase** (spec §23) — a real
  scope gap, not implemented. `/cat/[id]`, `/story/[id]`, and
  `/portrait/[id]` still render fine when shared (their own existing
  page metadata, from earlier phases, is unaffected), but a link to
  `/explore` itself or to a specific breed/personality/color filter
  won't carry a rich, cat-specific preview.
- **No public "like" mechanism exists, by design** (spec §21) — "Save
  to My Collection" (Phase 9) is the intentional substitute; a public
  cat's popularity is instead represented honestly via the new, real
  `most_discovered` sort (a genuine visitor count), never a fabricated
  like/heart tally.
- **No cat/non-cat detection gate exists** (Phase 16 finding, the most
  important one in this report) — the breed classifier will confidently
  assign a specific cat breed to any valid image, including real,
  clearly-non-cat photos (a dog photo scored "Abyssinian" at 94.52%
  confidence in direct testing). Evaluated and documented per Phase 16
  spec §8's explicit instruction not to bolt on a new model without a
  scoped implementation plan — proposed as a future phase, not built.
  See AI_VALIDATION_REPORT.md §7.
- **4.4% of breed-classifier test predictions are confidently (≥80%)
  wrong** (16 of 360 real test-set images) — a real, measured rate,
  not previously surfaced this explicitly. See
  AI_VALIDATION_REPORT.md §6.
- **No formal similarity retrieval benchmark exists** — there is no
  labeled "these two specific photos are the same cat" ground-truth
  dataset available, and none was invented. Mathematical correctness
  (identical/orthogonal/opposite/ranked vector tests) and real
  qualitative retrieval are verified instead; formal retrieval
  accuracy is explicitly `NOT VERIFIED`, not approximated.
- **Fur color remains a visual estimation, not a colorimetric
  measurement** (unchanged framing since Phase 5) — now additionally
  confirmed *deterministic* as of Phase 16's bug fix, which it wasn't
  before.
- Previously noted limitations (no live Anthropic/`gpt-image-1` API
  call tested, local dev Postgres on port 5433, the ML-less Docker
  image, `vitest.config.ts`'s `pool: "threads"`, single global FAISS
  index with SQL-enforced privacy, no Open Graph metadata for
  `/explore`) are unchanged from Phase 9–15.

## Next Steps

Begin Phase 17: Production Readiness — the next un-started item in
ROADMAP.md (Docker/CI-CD hardening, formal component/E2E test
expansion, and closing the remaining honest gaps this report
surfaces). A cat/non-cat detection gate (AI_VALIDATION_REPORT.md §7)
is the single highest-value scoped follow-up if a future phase wants
to address it — genuinely useful, deliberately not built in Phase 16.
If a real `ANTHROPIC_API_KEY` or `IMAGE_GENERATION_API_KEY` ever
becomes available in this environment, a live-call smoke test for both
providers remains a high-value, currently-missing piece of
verification. Open Graph metadata for `/explore` and its filtered
views would be a reasonable, scoped follow-up before Phase 15's
discovery feature is considered fully polished for sharing.

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
- **Always re-verify a claim like "X doesn't exist in this repo" with a
  direct, working search before writing it into a report** — Phase 13
  claimed zero frontend tests existed anywhere, based on a `Glob` call
  that (for reasons not fully diagnosed) returned no results even
  though `git ls-files | grep test` immediately found 22 real,
  passing test files going back to the initial commit. The fix wasn't
  just correcting the doc — it was cross-checking with a second,
  different tool (`git ls-files`) before trusting a negative search
  result enough to state it as fact. A negative result from one tool
  is weaker evidence than a positive result; worth a second check
  before it becomes a permanent claim in a report or a doc.
- **Extending an existing ABC with one new method beats standing up a
  parallel provider hierarchy** — `ImageGenerationProvider` already
  existed (Phase 13, unused) with `generate_wallpaper`/`generate_avatar`
  placeholders for a different feature; adding `generate_portrait`
  alongside them (rather than creating a second, portrait-specific
  provider interface) kept `get_image_generation_provider()`'s factory
  shape, the `NullProvider` fallback pattern, and the "check
  `is_available` before touching anything real" convention all
  consistent with `get_llm_provider()` — no new architecture to learn.
- **A prompt-injection test is cheap to write and catches a real class
  of bug**: appending untrusted user text to a prompt string and
  asserting *where* it can and can't land (via a fixed section order —
  identity/known-signals/style always come first, user text always
  last) is easy to verify mechanically (`prompt.split("STYLE:")[0]`
  must never contain the injected text) without needing an LLM in the
  loop at all, since the guarantee lives in Python string
  concatenation order, not in hoping the model ignores an injected
  instruction.
- Previously noted lessons (DB-backed sessions over JWT, ownership-
  scoped queries as the security boundary, the idempotent-event-log
  pattern, content-hash deduplication, model versioning via a
  cache-key unique constraint, the two-table cheap-core/expensive-extra
  caching split, schema-shape-as-guarantee over prompt instructions,
  shared-dev-corpus test flakiness) all still apply.
- **A rate limit sized for one class of endpoint can quietly break a
  different class it was never designed for** — this phase's
  `enforce_rate_limit` (20/min) was correctly sized for AI-cost-bearing
  endpoints (analyze, story, personality, portrait generation), but
  reusing it unmodified for `/explore`'s read-only browsing endpoints
  broke on the very first real Playwright run: one page load fires 5
  parallel requests, and a couple of filter clicks exhausted the
  budget within seconds. This was invisible in unit tests (which don't
  exercise five simultaneous real HTTP requests the way a browser
  does) and only surfaced via a live E2E run — a concrete reminder that
  "reuse the existing rate limiter" (a correct instruction) doesn't
  automatically mean "reuse the existing *threshold*." Worth checking,
  for any future endpoint, whether its actual request pattern (how
  many calls does one real user action generate?) matches the budget
  it's about to inherit, not just whether a `RateLimiter` dependency
  exists to attach.
- **A computed-not-stored field can be a *better* filtering source than
  a cached one, not just an acceptable shortcut** — Phase 15 filters
  and groups public cats by Phase 13's personality archetype without
  ever touching the `cat_personalities` table (which only has a row
  for a cat once someone has opened its Personality card — an
  incomplete, view-order-dependent index). Recomputing the archetype
  in-process from already-loaded columns is both cheap (sub-millisecond,
  confirmed in Phase 14) and *more correct* for browse-time use than
  joining a lazily-populated cache table would have been. Worth
  reaching for "just recompute it" before "join the cache table"
  whenever the computation is genuinely cheap and the cache table's
  population is incomplete or order-dependent.
- **`useInfiniteQuery` is worth reaching for immediately, not after
  writing a manual `page`/`accumulated` state pair** — the first draft
  of the `/explore` page used local `useState` plus two `useEffect`s to
  reset and accumulate pages, which `eslint-plugin-react-hooks`'
  newer `set-state-in-effect` rule correctly flagged as a real
  cascading-render risk. Rewriting to TanStack Query's built-in
  infinite-list primitive (`initialPageParam`/`getNextPageParam`)
  deleted both effects entirely and was less code, not just
  lint-clean code — a sign the manual version was solving a problem
  the library already solves, not a case of the lint rule being overly
  strict.
- Previously noted lessons (DB-backed sessions over JWT, ownership-
  scoped queries as the security boundary, the idempotent-event-log
  pattern, content-hash deduplication, model versioning via a
  cache-key unique constraint, the two-table cheap-core/expensive-extra
  caching split, schema-shape-as-guarantee over prompt instructions,
  shared-dev-corpus test flakiness) all still apply.
- **"Fix" a flaky test by removing the actual source of non-uniqueness,
  not by picking a more distinctive constant** — Phase 13 first hit
  `test_similarity.py`'s fixture-pollution bug and patched it with a
  more "distinctive" hardcoded color; Phase 16 hit the *same* test
  failing again, for the *same* underlying reason, because a hardcoded
  constant re-run across many local regression cycles is never
  actually unique — only the specific *value* changed, not the fact
  that it was reused every run. Direct measurement (querying the DB
  for how many rows shared one `vector_id`) found 52 accumulated
  duplicates before diagnosing this properly. The durable fix
  generates the fixture value fresh (`uuid4`) on every single test
  run, which no amount of repeated local execution can ever collide
  with itself. When a "fixed" flaky test flakes again later, the right
  question is "why did the fix stop working," not "what's a better
  constant" — a recurring flake is itself a signal the first fix
  treated a symptom.
- **A library call that accepts one seed parameter doesn't mean every
  source of randomness in the pipeline is seeded** — `cv2.grabCut` sits
  immediately upstream of `KMeans(random_state=42)` in the fur-color
  pipeline, and it would be reasonable to assume the pipeline was
  therefore fully deterministic. It wasn't: OpenCV's GrabCut draws from
  its *own* internal RNG (`cv2.setRNGSeed`), entirely separate from
  scikit-learn's `random_state` mechanism, silently. Worth explicitly
  testing determinism end-to-end (call the real public method N times,
  compare outputs) rather than inferring it from seeing one seed
  parameter set somewhere in the call chain.
- **When adding a new third-party SDK, check whether it needs the same
  logging treatment as the SDKs already suppressed** — `anthropic`'s
  logger was deliberately suppressed to `WARNING` in Phase 6 with a
  clear rationale (it can echo request/response payloads at `DEBUG`,
  including auth headers). `openai` (Phase 14) has the exact same risk
  profile and its own separate logger namespace, but wasn't added to
  the same list — an easy thing to miss because the app kept working
  fine either way; the gap was only visible by actually reading
  `configure_logging` line by line and asking "does this cover every
  AI SDK currently imported," not by anything failing.
