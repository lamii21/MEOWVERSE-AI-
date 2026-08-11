# MeowVerse AI — Project Status

_Last updated: 2026-08-11_

## Current Phase

**Phase 10 — MeowVerse Cat Universe: Collection, Gamification &
Discovery: complete and verified end-to-end.** Phase 11 is next, not
yet started.

## What Exists

- `backend/` —
  - `app/models/progress.py` — `UserProgressModel`, one row per user
    (`user_id` as the primary key, a genuine 1:1), `xp` (Integer). No
    `level` column — level is always derived from `xp` on read
    (`app/services/progression.py`), so the two can never drift.
  - `app/models/collection_event.py` — `CollectionEventModel`, an
    append-only log of XP-awarding events, unique on
    `(user_id, event_type, target_id)`. This unique constraint is the
    entire anti-XP-farming mechanism — see ARCHITECTURE.md §15.
  - `app/services/progression.py` — `XP_VALUES` (the 5 event → XP
    amounts), `level_for_xp`/`xp_required_for_level`/`title_for_level`
    (quadratic curve, `100 × (N-1)²`, capped at level 20),
    `LevelProgress` (bundles everything a progress bar needs from one
    `xp` value).
  - `app/services/breed_catalog.py` — `get_supported_breeds()`, the
    canonical 12-breed universe read from `ml/models/class_names.json`
    (not the demo-mode 5-breed pool) — the fixed denominator for
    collection completion %.
  - `app/repositories/progress_repository.py`,
    `event_repository.py` — `add_xp` (atomic `xp = xp + :amount`
    UPDATE, not read-modify-write), `record_event_if_new`
    (`ON CONFLICT DO NOTHING ... RETURNING`, returns whether XP should
    actually be granted), `count_events`.
  - `app/services/gamification.py` — `process_event(db, user_id,
    event_type, target_id, *, is_new_breed=False, is_new_rarity=False)`
    — the one function every gamification-triggering endpoint calls.
    Grants event XP idempotently, re-syncs achievements, grants
    achievement-unlock XP for any newly-qualified ones, detects a
    level-up, returns a `GamificationEvent`.
  - `app/services/achievement_definitions.py` — extended from Phase
    9's 5 to 9: `first_meow` ("First Paw"), `cat_explorer` ("Cozy
    Collector"), `collector`, `rare_hunter` ("Rare Hunter", new),
    `legendary_hunter` ("Royal Encounter"), `rainbow_collector`
    ("Color Collector"), `storyteller` (new), `dream_keeper` (new),
    `cat_home` (new). Existing keys were relabeled, never renamed —
    an already-unlocked achievement never "re-locks." Each definition
    now also exposes `progress(stats) -> (current, target)` for the
    UI's progress bars.
  - `app/schemas/achievement.py` — `AchievementOut` extracted into its
    own leaf module (no imports of other `app.schemas` modules)
    specifically to break a real circular import:
    `analysis.py → gamification.py → collection.py → analysis.py`.
    Same pattern as Phase 3's `schemas/common.py` extraction.
  - `app/schemas/gamification.py` — `GamificationEvent` (xp_awarded,
    total_xp, level, leveled_up, is_new_breed, is_new_rarity,
    newly_unlocked). Attached to `AnalysisResult.gamification` and
    `StoryResponse.gamification` — `None` on any plain `GET`.
  - `app/schemas/collection.py` — `CollectionStats` extended
    (`rare_count`, `unique_breeds_discovered`,
    `total_supported_breeds`, `completion_percentage`,
    `unique_colors_discovered`, `rarity_distribution` zero-filled
    across all 6 tiers); new `BreedDiscoveryOut`, `ProgressOut`.
  - `app/schemas/analysis.py` — `AnalysisResult` gained `created_at`
    and `has_story` (a real query, batched for the collection list via
    `story_repository.get_analysis_ids_with_stories` to avoid N+1 —
    one extra query for the whole page, not one per row).
  - `app/repositories/analysis_repository.py` — `get_rarity_distribution`,
    `get_discovered_breeds`, `get_breed_discovery_stats`,
    `is_first_of_breed`/`is_first_of_rarity` (recomputed fresh from
    real rows every time, never a stored flag); `list_user_analyses`
    gained a `has_story` filter and extended sort
    (`name_asc`/`name_desc`/`breed`/`favorite`, replacing the old
    single `"name"` value); `get_user_stats` gained `rare_count`.
  - `app/repositories/story_repository.py` — `has_story_of_style`
    (Dream Keeper), `has_any_story`/`get_analysis_ids_with_stories`
    (has_story on single/list responses).
  - `app/api/v1/analyses.py` — `create_analysis`, `save_cat`,
    `favorite_cat`, `share_cat` now each call into gamification and
    attach the resulting `GamificationEvent`; `unfavorite_cat`/
    `unshare_cat` deliberately don't (those aren't discovery moments).
  - `app/api/v1/stories.py` — `create_story` now takes
    `get_current_user_optional`; grants `STORY_GENERATED` XP only when
    the caller is authenticated *and* owns the analysis (guests, and
    generating a story for someone else's cat via a known id, still
    work exactly as before — Phase 7/9 behavior unchanged — just never
    grant XP).
  - `app/api/v1/collection.py` — new `GET /api/v1/me/breeds` (Breed
    Explorer), `GET /api/v1/me/progress` (XP/level); `/collection`
    gained `has_story`/extended `sort` query params. All under the
    established `/api/v1/me/` prefix rather than the spec's suggested
    standalone `/api/v1/collection/*` paths — one "current user"
    namespace, not two.
  - Migration `376d7d0d1186` — adds `user_progress`,
    `collection_events`. No changes to any existing table; verified
    via a real upgrade → downgrade → upgrade cycle.
  - Tests: `test_progression.py` (level formula, pure unit tests),
    `test_gamification.py` (30 tests: XP idempotency for every event
    type, guest/cross-user XP denial, breed-duplicate handling,
    completion-percentage formula self-consistency, rarity-distribution
    zero-filling, achievement unlock via real events, Breed Explorer
    correctness/isolation, progress endpoint isolation).
    **170/170 backend tests passing** (was 140), ruff clean.
- `frontend/` —
  - `types/achievement.ts`, `types/gamification.ts` — leaf types,
    same circular-import-avoidance reasoning as the backend split.
  - `types/collection.ts` — extended `CollectionStats`, new
    `BreedDiscovery`, `Progress`; `CollectionSort` extended to match
    the backend.
  - `types/analysis.ts`, `types/story.ts` — gained `gamification`;
    `AnalysisResult` gained `created_at`/`has_story`.
  - `lib/discovery-toast-store.ts` — a `useSyncExternalStore`-based
    queue (same pattern as Phase 7's SSR-safe external-state hooks,
    chosen over React Context since producer and consumer have no
    parent/child relationship). Decomposes one `GamificationEvent`
    into up to 4 sequential toasts (breed → rarity → each achievement
    → level-up) — never shows the same discovery twice, never stacks.
  - `features/gamification/` — `use-discovery-toast.ts`,
    `components/DiscoveryToastHost.tsx` (mounted once in
    `app/layout.tsx`, soft glow + gentle scale, reduced-motion-aware),
    `components/ProgressCard.tsx` (XP/level bar).
  - `features/collection/components/BreedExplorer.tsx`,
    `CollectionMap.tsx` (the constellation view — deterministic
    per-cat hash positions, capped at 60 nodes, a plain list fallback
    below `sm`), `CollectionCard.tsx` extended (story-availability
    icon, real discovery date).
  - `app/collection/page.tsx` — full "My Cat Universe" redesign:
    header, 6 real stat chips, `ProgressCard`, extended filters
    (rarity tiers + Favorites + Stories + Recently Discovered),
    debounced search, extended sort, pagination, collapsible Map and
    Breed Explorer sections.
  - `app/achievements/page.tsx` — new: unlocked (with unlock dates)
    and locked (with real progress bars) sections.
  - `app/profile/page.tsx` — gained `ProgressCard`, 4 more stat tiles
    (rare+, completion%, breeds found, colors found), a "favorite cat"
    preview (reuses the existing collection endpoint filtered/sorted
    rather than a new one), a link to the full `/achievements` page.
  - `features/auth/components/AppNavbar.tsx` — `/achievements` added
    as a real nav link; the old icon-only Trophy shortcut (→
    `/profile#achievements`) removed as redundant.
  - `hooks/use-debounced-value.ts` — new, small, generic.
  - 6 new/extended test files (`discovery-toast-store.test.ts`,
    `ProgressCard.test.tsx`, `DiscoveryToastHost.test.tsx`,
    `BreedExplorer.test.tsx`, extended `CollectionCard.test.tsx`, plus
    fixture updates in `CatCard.test.tsx`/`StoryCard.test.tsx`/
    `StorySection.test.tsx` for the new response fields).
    **85/85 frontend tests passing** (was 69), lint/build clean.

## Real Results (Phase 10)

- **Both suites green**: 170/170 backend (pytest, real Postgres),
  85/85 frontend (Vitest + RTL).
- **Verified end-to-end via a live, scripted Playwright run** against
  real `uvicorn` + `next dev` servers, the spec's flow: register →
  analyze first cat → verify collection count (1) and XP (150 — 100
  discover + 50 First Paw) → verify First Paw unlocked → analyze a
  second cat with the *same* image (same demo breed) → verify total
  cats went to 2 but unique-breed count didn't move → favorite the cat
  → generate a story → verify Storyteller progress (1/5) → open
  collection, filter by rarity, search by breed → open the cat's
  detail page → open `/achievements` → open `/profile` → refresh and
  confirm XP is unchanged → logout → confirm `/collection` redirects
  to `/login` → login again → confirm XP/level are exactly what they
  were before logout. All steps passed.
- **Responsive QA** at 320/375/390/768/1024/1440px on `/collection`
  (map + Breed Explorer expanded), `/achievements`, `/profile` — zero
  horizontal overflow at any width, confirmed programmatically
  (`document.documentElement.scrollWidth` vs `clientWidth`) as well as
  visually. The Collection Map correctly swaps to its plain-list
  fallback below `sm`.
- **Reduced motion verified working** — and along the way, a real bug
  was found and fixed (not introduced this phase): `AuthCard.tsx`
  (built in Phase 9) conditioned its Framer Motion `initial` prop
  directly on `useReducedMotion()`, which — unlike the deferred-to-effect
  read this codebase's Phase 8 notes describe — is applied as a real
  SSR-rendered inline style; a client whose OS already prefers reduced
  motion disagreed with the server's default-`false` render on the very
  first paint, a genuine React hydration mismatch on `/login` and
  `/register`. Caught via Playwright's `reducedMotion: "reduce"`
  context option hitting a fresh page load (something Phase 9's own
  reduced-motion QA hadn't happened to exercise). Fixed by keeping
  `initial` constant regardless of `reduceMotion` and gating only the
  transition `duration` — SSR and client-first-render now always agree.
  Verified via a dedicated re-run: zero console errors.

## What Does Not Exist Yet

Image generation (Phase 13), advanced analytics, a mobile app, a
social feed, chat, OAuth login, daily/recurring engagement mechanics
(explicitly out of scope per the Phase 10 brief — "not a gambling-like
system"), deleting a cat from your collection (still deferred — see
ROADMAP.md's Phase 10 entry for why), Redis-backed rate limiting and
S3-compatible image storage (both behind ready interfaces, only the
dev-grade implementation exists). See ROADMAP.md Phases 11–17.

## Known Limitations / Honest Gaps

- **Demo-mode breed completion caps at 4/12 ≈ 33%.** Only 4 of the 5
  demo-mode breed labels are members of the canonical 12-breed
  universe (`"Domestic Shorthair"` isn't) — a user running without the
  real trained classifier installed can never reach full breed
  completion no matter how many cats they analyze. This is documented,
  not hidden; see ARCHITECTURE.md §17.
- **The MeowVerse Map shows at most 60 stars**, sourced from whatever
  page of the collection grid is currently loaded/filtered (not a
  separate full-collection fetch) — a deliberate performance/simplicity
  tradeoff so opening the map never costs an extra unbounded query.
- **XP/achievements/breed-discovery stats are computed live on every
  request** (a handful of indexed aggregate queries each) — fine at
  this project's scale; would need caching or a materialized rollup
  well before it stopped being fine at real scale.
- **"Recently Discovered" is an alias for sort=newest**, not a real
  time-window filter (e.g. "last 7 days") — deliberately not invented,
  since any specific threshold would be a fabricated definition the
  spec didn't ask for. Documented in code, not just here.
- Previously noted limitations (rate limiting in-memory/single-process,
  local-disk-only image storage, client-side-only route protection, the
  one architecturally-unavoidable guest 401, no live Anthropic API call
  tested, local dev Postgres on port 5433, the ML-less Docker image,
  `vitest.config.ts`'s `pool: "threads"`) are all unchanged from Phase 9.

## Next Steps

Begin Phase 11: Similarity Search (embedding generation + a FAISS
index, a `/api/cats/{id}/similar` endpoint and UI) — the next
un-started item in ROADMAP.md, and nothing from Phase 10's explicit
scope was deferred into it.

## Notes for Future Sessions

- **An idempotent event log (unique constraint + `ON CONFLICT DO
  NOTHING ... RETURNING`) is the simplest correct way to make a
  reward system un-farmable** — cheaper and easier to reason about
  than trying to rate-limit or debounce the triggering actions
  themselves. Award XP only when the insert actually happened.
- **Level should be derived from XP on every read, never stored
  redundantly** — two numbers that are supposed to always agree will
  eventually disagree if there are two of them.
- **A schema field that needs to satisfy `mutation_response → some
  other resource's shape` is a circular-import risk** — the fix is
  always the same: extract the shared shape into its own leaf module
  with zero sibling imports (this codebase's second time doing this,
  after Phase 3's `schemas/common.py`; recognize the shape early next
  time).
- **`useReducedMotion()` being read directly into a Framer Motion
  `initial` prop can cause a genuine SSR hydration mismatch**, not
  just the "stale value in a `useState` initializer" issue Phase 8
  already documented — `initial` renders as a real inline style during
  SSR, so conditioning it on any client-only value risks disagreeing
  with the server's default render. The fix is to keep `initial`
  constant and gate the `transition` `duration` instead. Found in
  `AuthCard.tsx` this phase via Playwright's `reducedMotion: "reduce"`
  context option — worth reaching for that option specifically on any
  page that's genuinely SSR-rendered with real content on first load
  (not one that's client-only/gated behind a toggle, which doesn't
  carry the same risk).
- Previously noted lessons (Base UI quirks, dark-mode media-query
  strategy, forced-tool-use for structured LLM output, the
  `useSyncExternalStore` pattern for SSR-safe external state, the
  ref-returned-from-a-hook React Compiler lint gotcha, DB-backed
  sessions over JWT, ownership-scoped queries as the security
  boundary, the logout hard-navigation race fix) all still apply.
