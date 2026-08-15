# MeowVerse AI — Project Status

_Last updated: 2026-08-15_

## Current Phase

**Phase 12 — MeowVerse Explainable AI: Real Grad-CAM Breed
Explanations: complete and verified end-to-end.** Phase 13 is next,
not yet started.

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

## What Does Not Exist Yet

Image generation (Phase 13), advanced analytics, a mobile app, a
social feed, chat, OAuth login, a formal Grad-CAM faithfulness
*benchmark* (a small sanity check was performed and is documented
above — a rigorous benchmark with a held-out evaluation protocol is a
different, larger undertaking not attempted), pgvector, deleting an
analysis. See ROADMAP.md Phases 13–17.

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
- Previously noted limitations (no live Anthropic API call tested,
  local dev Postgres on port 5433, the ML-less Docker image,
  `vitest.config.ts`'s `pool: "threads"`, single global FAISS index
  with SQL-enforced privacy) are unchanged from Phase 9–11.

## Next Steps

Begin Phase 13: Creative Generation (`ImageGenerationProvider`
interface + fallback UI, wiring up the Cat Card's existing "Generate
Wallpaper" placeholder button) — the next un-started item in
ROADMAP.md.

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
