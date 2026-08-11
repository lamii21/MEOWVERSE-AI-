# MeowVerse AI — Project Status

_Last updated: 2026-08-11_

## Current Phase

**Phase 8 — Magical Experience & Cat Card: complete and verified
end-to-end.** Phase 9 (Auth & Persistence) is next, not yet started.

## What Exists

- `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_STATUS.md`, `README.md`
- Git repository initialized at project root (nothing committed yet —
  commits happen only when explicitly requested)
- `backend/` —
  - `app/models/analysis.py` — `CatAnalysisModel` gained `is_public`
    (Boolean, default `False`), same explicit-share-only contract as
    `stories.is_public` from Phase 7. Migration `d64ea3d2f0bd`.
  - `app/repositories/analysis_repository.py` — new
    `get_public_analysis`/`set_public`, mirroring the story
    repository's equivalents.
  - `app/schemas/analysis.py` — `AnalysisResult` gained `is_public: bool`.
  - `app/api/v1/analyses.py` — new `GET /api/v1/analyses/{id}` (404
    unless public) and `POST /api/v1/analyses/{id}/share` (idempotent),
    backing the new `/cat/[id]` public Cat Card page. A `_row_to_result`
    helper converts a `CatAnalysisModel` row back into the full
    `AnalysisResult` shape (breed/colors/profile all reconstructed from
    the persisted JSONB).
  - Tests: 6 new tests in `test_analyses.py` (private-by-default,
    404-when-private, share-makes-public, share-is-idempotent,
    share-nonexistent-404, nonexistent-cat-404). **81/81 backend tests
    passing** (was 75).
- `frontend/` —
  - `features/results/` — new feature area entirely:
    - `rarity.ts` — `RARITY_VISUALS`, a config object mapping each of
      the 6 `Rarity` values to a `tier` (1–6), a `treatment`
      (plain/tint/shimmer/glow/aura/particles), and card/badge
      classNames.
    - `use-card-tilt.ts` — pointer-driven 3D tilt via Framer Motion
      springs (`rotateX`/`rotateY`), no WebGL. Takes the target ref as
      a parameter rather than creating one internally and returning it
      bundled in an object — the latter isn't statically recognizable
      as a ref by the `react-hooks/refs` (React Compiler) lint rule,
      which then flags every read of it.
    - `use-saved-cat.ts` — local "Save" bookmark, `localStorage` +
      `useSyncExternalStore` (same pattern as Phase 7's story-favorite
      hook, same SSR-hydration-safety reason).
    - `components/ResultReveal.tsx` — the cinematic intro beat, then a
      render-prop (`children(interactive: boolean)`) handing off to
      the caller's layout.
    - `components/CatCard.tsx` — the collectible card: image, name,
      title, breed, rarity badge, magic power, personality,
      `ConfidenceMeter`, `ColorPalette`, description, MeowVerse ID
      (short id derived from the analysis UUID), and the action row
      (Save/Share/Download PNG/Story/Wallpaper).
    - `components/RarityAura.tsx` — per-tier animated flourish,
      reduced-motion-aware (every animated variant has a static
      equivalent).
    - `components/ConfidenceMeter.tsx`, `components/ColorPalette.tsx`
      — small presentational components.
    - `components/ResultExperience.tsx` — top-level composition used
      by `/analyze`: two-column desktop layout (Cat Card sticky-left,
      story + transparency panel right), single-column on mobile.
    - `components/PublicCatView.tsx` — read-only wrapper around
      `CatCard` used by `/cat/[id]`.
  - `app/cat/[id]/page.tsx` — new. Server component mirroring Phase
    7's `/story/[id]`: fetches via `fetchPublicAnalysis`, `notFound()`
    on 404.
  - `services/analyses.ts` — new `shareAnalysis`, `fetchPublicAnalysis`;
    `AnalysisErrorKind` gained `"not_found"`.
  - `types/analysis.ts` — `AnalysisResult` gained `is_public: boolean`.
  - `features/analyze/components/HowMeowVerseKnows.tsx` — visually
    regrouped into two clearly labeled sections ("Real computer
    vision" vs "Generative AI") instead of only being distinguishable
    by icon color.
  - `features/analyze/components/DemoResultSummary.tsx` — **deleted**,
    replaced by `ResultExperience`. It was an explicitly-labeled Phase
    3 placeholder ("The full magical results page... arrives in a
    later phase") — this phase is that later phase.
  - `app/globals.css` — fixed a real, previously undiscovered bug from
    Phase 2: `--font-sans: var(--font-sans)` was self-referential, so
    the entire app had silently been falling back to the browser's
    default serif font instead of Geist Sans since the design system
    was first built. Now `--font-sans: var(--font-geist-sans)`.
  - `components/ui/progress.tsx` — not modified, but a real usage
    footgun was discovered and worked around: `Progress` always
    renders its own default track+indicator *in addition* to any
    children passed to it, so `ConfidenceMeter` initially rendered two
    stacked bars until its custom children were removed in favor of
    the default styling.
  - `package.json` — added `html-to-image` (PNG export).
  - 6 new test files (27 new tests): `rarity.test.ts`,
    `use-card-tilt.test.ts`, `ConfidenceMeter.test.tsx`,
    `ColorPalette.test.tsx`, `ResultReveal.test.tsx`, `CatCard.test.tsx`.
    **51/51 frontend tests passing** (was 24).

## Real Results (Phase 8)

- **Both suites green**: 81/81 backend (pytest, real Postgres),
  51/51 frontend (Vitest + RTL).
- **Verified end-to-end via a live, scripted Playwright run** against
  real `uvicorn` + `next dev` servers: landing → upload → analyze →
  cinematic reveal ("A new cat has appeared...") → Cat Card settles →
  pointer-tilt hover → Save → Share (clipboard-copy fallback, since
  headless Chromium has no native share sheet) → Download PNG (a real
  1.1MB, non-blank PNG file, inspected visually) → Generate Story
  (reused the Phase 7 flow unchanged) → opened the shared `/cat/[id]`
  link in a new tab and confirmed it rendered the same card, correctly
  still showing "Saved" (same `localStorage`) → responsive screenshots
  at 320/375/390/768/1024/1440px → a separate full run with Playwright
  `reducedMotion: "reduce"` emulation confirming the intro beat is
  skipped and the card is immediately interactive. **Zero console
  errors on the final run.**
- **Five real bugs found and fixed during verification, not glossed
  over** (in the order discovered):
  1. `html-to-image`'s `cacheBust: true` option appends a `?timestamp`
     query string to every image src to force a fresh fetch — but the
     cat photo's src is a `blob:` URL, which doesn't support query
     strings at all, so every export attempt threw. Removed (and
     unnecessary anyway for a one-shot export).
  2. A genuine `useReducedMotion()` race in `ResultReveal`: framer-motion's
     hook resolves asynchronously (defers to an internal effect so
     it's SSR-safe), so reading it directly in a `useState` initializer
     always captured its pre-resolution default (`false`) — the full
     animated intro played once even with the OS preference set,
     before the state caught up. Fixed with a dedicated syncing effect.
  3. `app/globals.css`'s `--font-sans: var(--font-sans)` self-reference
     — a Phase 2 bug that had been silently active through every prior
     phase's screenshots, only caught because Phase 8's typography
     focus prompted a close look at rendered text.
  4. `ConfidenceMeter` rendered two stacked progress bars — the shared
     `Progress` component always appends its own default track
     regardless of what children are passed to it.
  5. The magic-power `Badge` clipped its text off the edge of the card
     — `Badge` is `whitespace-nowrap` (built for short tags), but
     `magic_power` can be a full sentence. Rendered as wrapping plain
     text instead.
- **PNG export produces a real, complete file** — verified by
  inspecting the actual downloaded 1.1MB PNG (not just checking that a
  download event fired): correct layout, rarity gradient, all text,
  the confidence meter, and the color palette all present and legible.

## What Does Not Exist Yet

Image generation (Phase 13 — Wallpaper button is a labeled placeholder
only), full auth, the full Phase 9 database schema (users, favorites,
achievements), a page to browse "Saved" cats (Phase 8's Save is a
local bookmark with nowhere to view the list yet — Phase 10),
collection/achievements, similarity search, Grad-CAM, full E2E test
suite (Phase 14), a `mood` signal (mentioned as "if available" in the
Phase 8 brief — no such field exists in `CatProfile`, so the Cat Card
honestly omits it rather than fabricate one). See ROADMAP.md Phases
9–17.

## Known Limitations / Honest Gaps

- **`is_public` sharing has no ownership/auth check**, for both
  stories (Phase 7) and analyses (Phase 8) — anyone who knows a UUID
  (not enumerable) can make it public. Acceptable for now: there's no
  user/auth system at all yet (Phase 9), and the action is additive/
  idempotent (can only reveal, never mutate or delete).
- **Save is local-only.** `use-saved-cat.ts` bookmarks to
  `localStorage`, not a real per-user collection — there's no backend
  table for it, and no page to browse saved cats yet (Phase 10). The
  Phase 8 brief listed "Save" and "Favorite" as separate actions;
  they were deliberately consolidated into one button since two
  divergent local-only flags with no collection page to view either
  against would have been dead-end UI — documented as a scope decision,
  not an oversight.
- **Generate Wallpaper is a real, honest placeholder** — disabled with
  a `title="Coming in a future update"` tooltip, not a button that
  pretends to work. Depends on `ImageGenerationProvider` (Phase 13,
  still a null stub).
- **No live Anthropic API call tested** — unchanged gap from Phases 6–7.
- **Local dev Postgres on host port 5433** — unchanged from Phase 7
  (native Windows Postgres service conflict on 5432).
- **Docker gap unchanged from Phase 4/5**: the backend image doesn't
  install `requirements-ml.txt`, so breed/color analysis stay demo-mode
  in containers.
- **Rate limiting is in-memory, single-process** — unchanged from
  Phase 6.
- **`vitest.config.ts` uses `pool: "threads"`** — unchanged from
  Phase 7 (Windows + OneDrive-synced-path-with-a-space environment
  quirk).

## Next Steps

Begin Phase 9: Auth & Persistence. Email/password auth, secure
password hashing, token issuance, the full DB schema (users,
cat_profiles, analysis_results, generated_assets, favorites,
achievements — building out from Phase 7/8's minimal `cat_analyses`/
`stories` subset), and real analysis history so Phase 8's local-only
"Save" can grow into an actual per-user collection.

## Notes for Future Sessions

- **A hook that creates a ref and returns it bundled inside an object
  isn't statically recognizable as a ref by the `react-hooks/refs`
  (React Compiler) lint rule** — every read of `returnedObject.ref` in
  JSX then gets flagged as an unsafe render-time ref access. Fix: have
  the *consuming* component create the ref via its own `useRef()` call
  and pass it *into* the hook, rather than the hook creating and
  returning one. Found and fixed in `use-card-tilt.ts` this phase.
- **`useReducedMotion()` (and any hook backed by a browser media query)
  resolves asynchronously for SSR-safety** — it returns its default
  value on the very first render and only reflects the real value
  after an internal effect fires and triggers a re-render. Reading it
  directly in a `useState` initializer captures the stale default
  permanently for that state variable; it needs its own syncing
  `useEffect` (see `ResultReveal.tsx`) if the initial render must
  reflect the real preference. Found and fixed in `ResultReveal.tsx`
  this phase. This is the second time this exact shape of bug has
  appeared in this codebase (`useSyncExternalStore` solved the
  analogous `localStorage`-read version of it in Phase 7) — worth
  remembering as a category, not just a one-off fix.
- **A shared UI primitive's implicit behavior can silently double up
  markup**: `components/ui/progress.tsx`'s `Progress` renders
  `{children}` *and then* its own default `ProgressTrack`+`ProgressIndicator`
  unconditionally — passing a custom track as children doesn't replace
  the default, it adds a second one. Worth checking any shared
  component's actual render output (not just its prop types) before
  assuming customization-via-children works the way it looks like it
  should.
- **`Badge` is `whitespace-nowrap` by design** (built for short,
  fixed-length tags) — never use it for a field whose content length
  isn't bounded by the schema (e.g. a free-text LLM-generated
  sentence). Plain wrapping text is the correct choice for those.
- **`html-to-image` (and canvas-export libraries generally) can't
  handle query strings appended to `blob:` URLs** — the `cacheBust`
  option is meant for cached *remote* images and actively breaks
  local blob-URL image sources. Skip it for one-shot exports of
  locally-sourced content.
- Previously noted Base UI quirks, the dark-mode media-query strategy,
  forced-tool-use for structured LLM output, the schemas/common.py
  circular-import fix, the `profile_mode`/`story_mode` vs
  `breed_mode`/`colors_mode` vocabulary distinction, the `useSyncExternalStore`
  pattern for SSR-safe external state (Phase 7), the `OxfordIIITPet`
  `_bin_labels` gotcha (Phase 4), and the "BaseModel doesn't require
  weights" pattern (Phase 5) all still apply.
