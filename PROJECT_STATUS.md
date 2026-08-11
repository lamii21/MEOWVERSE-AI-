# MeowVerse AI — Project Status

_Last updated: 2026-08-11_

## Current Phase

**Phase 9 — Authentication, User Accounts & Persistent Cat Collection:
complete and verified end-to-end.** Phase 10 is next, not yet started.

## What Exists

- `backend/` —
  - `app/models/user.py`, `session.py`, `achievement.py` — new
    `UserModel` (email unique+indexed, `password_hash` via bcrypt,
    display_name, avatar_url), `SessionModel` (opaque token hash,
    expiry, FK CASCADE to user), `UserAchievementModel` (unique on
    `user_id`+`achievement_key`).
  - `app/core/security.py` — `bcrypt` used directly (not
    `passlib[bcrypt]` — confirmed incompatible with installed bcrypt
    5.0.0 before writing any code), `secrets.token_urlsafe(32)`
    session tokens, SHA-256 token hashing for DB storage/lookup.
  - `app/core/auth_deps.py` — `get_current_user_optional` /
    `get_current_user` FastAPI dependencies, reading the session
    cookie and resolving it to a `UserModel`.
  - `app/core/csrf.py` — `verify_same_origin`, an `Origin`-header
    check applied to every mutating authenticated endpoint (see
    Security Decisions in ARCHITECTURE.md §11).
  - `app/repositories/user_repository.py`, `session_repository.py`,
    `achievement_repository.py` — new.
  - `app/services/auth_service.py` — register/authenticate/session
    create/lookup/logout; identical error for "no such email" and
    "wrong password" (no user enumeration).
  - `app/services/achievement_definitions.py`,
    `collection_service.py` — 5 achievements (First Meow, Cat
    Explorer, Collector, Rainbow Collector, Legendary Hunter),
    computed from real stored data on read, never fabricated.
  - `app/schemas/user.py`, `collection.py` — `UserOut` never includes
    `password_hash`; `UserCreate` validates password length + letter +
    digit.
  - `app/api/v1/auth.py` — `POST /register` (201, rate-limited),
    `POST /login`, `POST /logout` (204, CSRF-checked), `GET /me`,
    `PATCH /me` (CSRF-checked). Sets an httpOnly, `SameSite=Lax`
    session cookie.
  - `app/api/v1/collection.py` — `GET /api/v1/me/collection` (filter
    by rarity/favorites, search, sort, paginate), `GET
    /api/v1/me/stats`, `GET /api/v1/me/achievements`.
  - `app/storage/` — new `ImageStorageProvider` ABC +
    `LocalImageStorageProvider` (disk-backed, served at `/media`),
    interface shaped for a future S3-compatible swap. Never exposes
    storage credentials to the frontend.
  - `app/models/analysis.py` — gained `user_id` (nullable FK CASCADE —
    `NULL` means an unclaimed guest analysis), `cat_name`, `rarity`,
    `image_url`, `is_favorite`; two new composite indexes.
  - `app/repositories/analysis_repository.py` — ownership-scoped
    queries as the actual security boundary (every private-resource
    function filters by `user_id` in the SQL itself, not after the
    fact): `get_owned_analysis`, `claim_analysis` (atomic
    check-and-set, prevents guest-analysis hijacking), `set_favorite`,
    `set_public`/`set_private` (both ownership-gated), plus
    `list_user_analyses`, `get_user_stats`, `get_distinct_color_names`
    for the collection/stats endpoints.
  - `app/api/v1/analyses.py` — `create_analysis` now auth-optional
    (guests still get a full analysis, just unowned); new `POST
    /{id}/save` (claims a guest analysis), `/favorite`, `/unfavorite`,
    `/unshare`; `share_cat` now requires auth+ownership.
    `analysis_row_to_result` takes a required `viewer_is_owner: bool`
    kwarg with no default — see Security Decisions below, this is a
    fixed real privacy bug, not a hypothetical.
  - `app/api/v1/stories.py` — sharing/unsharing now auth+ownership
    gated, matching analyses.
  - `app/core/rate_limit.py` — rewritten behind a `RateLimiter`
    Protocol (`InMemoryRateLimiter` today, Redis-swappable later
    without touching call sites); a separately-keyed, tighter
    `enforce_auth_rate_limit` protects register/login specifically.
  - `app/core/config.py` — removed the pre-staged (unused) JWT
    settings; added session cookie name/expiry/secure-flag,
    auth-rate-limit threshold, image storage provider/dir settings.
  - Migration `b04f6df3d75b` — new `users`/`sessions`/
    `user_achievements` tables; `cat_analyses` gained `user_id`,
    `cat_name`, `rarity` (backfilled from existing JSONB on all 341
    pre-existing dev rows, then set `NOT NULL`), `image_url`,
    `is_favorite`. Verified via a real upgrade → downgrade → upgrade
    cycle with row-count/data-integrity checks at each step, not just
    a syntax check.
  - Tests: 4 new files — `test_auth.py` (16 tests: register/login/
    logout/me, duplicate email, wrong password, weak password,
    invalid session, rate-limit 429), `test_ownership.py` (guest vs.
    authenticated creation, private-access-denial across users, the
    save/claim flow, favorites, sharing-respects-ownership — including
    two dedicated regression tests for the privacy bug below),
    `test_collection.py` (collection filters/search/sort, stats never
    counting unowned guest analyses, achievements never unlocking from
    another user's activity), `test_csrf.py` (mismatched Origin
    actually rejected with 403, matching/missing Origin allowed).
    **140/140 backend tests passing** (was 81), ruff clean.
- `frontend/` —
  - `hooks/use-auth.ts` — TanStack Query IS the auth state store (no
    separate React Context): `useCurrentUser()`'s cached result under
    `["auth","me"]` is read everywhere via `useAuth()`
    (`status: "loading"|"authenticated"|"guest"`); `useLogin`/
    `useRegister`/`useLogout` mutate that cache directly.
  - `services/auth.ts`, `collection.ts` — all requests use
    `credentials: "include"` (httpOnly cookie auth, no token ever
    touches JS-readable storage).
  - `features/auth/components/AppNavbar.tsx` — auth-aware nav
    (Home/Discover/My Cats/Profile + Achievements/Logout when
    authenticated; Home/Discover/Login/Register as guest), with a
    hamburger menu for mobile (see Real Bugs Found below — the
    original desktop-only nav was unreachable below `md`).
  - `features/auth/components/AuthCard.tsx`, `GuestSavePrompt.tsx`,
    `RequireAuth.tsx` — shared auth-card chrome, the "create an
    account to save this cat" prompt guests see on Save, and
    client-side route protection for authenticated-only pages.
  - `app/login/page.tsx`, `app/register/page.tsx` — MeowVerse-styled
    (not generic forms), each wrapped in `<Suspense>` (Next.js 16
    requires this for `useSearchParams()` during static prerendering —
    a real, previously-undiscovered requirement hit this phase).
  - `features/results/use-cat-actions.ts` — Save/Favorite as TanStack
    `useMutation`s with optimistic updates and rollback-on-error via
    `onMutate`/`onError`.
  - `features/results/components/CatCard.tsx` — Save disabled once
    owned; Favorite is now its own persistent-backend button (was a
    local-only bookmark in Phase 8); Share disabled until owned;
    `GuestSavePrompt` rendered for guests.
  - `app/collection/page.tsx`, `app/collection/[id]/page.tsx` — real
    collection gallery: filters (All/Favorites/rarity tiers), search,
    sort (Newest/Oldest/Rarity/Name), empty state with a "Discover a
    Cat" CTA.
  - `app/profile/page.tsx` — display name, avatar, joined date, stats
    (total cats, favorite breed, most common color, legendary count,
    stories created — all computed from real stored data), achievements.
  - `app/settings/page.tsx` — display name update, logout.
  - Deleted `features/landing/components/Navbar.tsx` (superseded by
    `AppNavbar`) and `features/results/use-saved-cat.ts` (superseded
    by the persistent-backend favorite).
  - 5 new/rewritten test files (`use-auth.test.tsx`,
    `GuestSavePrompt.test.tsx`, `RequireAuth.test.tsx`,
    `CollectionCard.test.tsx`, fully rewritten `CatCard.test.tsx`) plus
    a shared `test-utils/render-with-query.tsx` helper.
    **69/69 frontend tests passing** (was 51), lint/build clean.

## Real Results (Phase 9)

- **Both suites green**: 140/140 backend (pytest, real Postgres),
  69/69 frontend (Vitest + RTL).
- **Verified end-to-end via a live, scripted Playwright run** against
  real `uvicorn` + `next dev` servers, the exact 21-step flow from the
  spec: guest analyze → view result → click Save → auth prompt appears
  → register → cat saved to the new account → refresh → still there →
  open collection → open the cat → favorite it → refresh → favorite
  persists → share it → open the public `/cat/[id]` page in a fresh
  context → confirm no private info (favorite/owned status, email,
  user id) leaks to a public viewer → logout → protected pages
  correctly redirect to login → login again → collection state fully
  restored. All 21 steps passed.
- **Responsive verification** at 320/375/390/768/1024/1440px.
- **Three real bugs found and fixed during verification, not
  hypothetical**:
  1. **Privacy leak**: the row→API-response converter computed
     `owned = owned or row.user_id is not None` even on the *public*
     viewing path, so any public `/cat/[id]` visitor saw `owned: true`
     and the real owner's `is_favorite` state. Found via my own
     security review before Playwright testing. Fixed by making
     `viewer_is_owner: bool` a required kwarg with no default, and
     unconditionally deriving `owned`/`is_favorite` from it. Covered
     by dedicated regression tests and reconfirmed live via the E2E
     script.
  2. **Logout race condition**: `router.push("/")` after logout raced
     against `RequireAuth`'s own redirect-to-login effect (which fires
     the instant the auth cache clears), so logging out from a
     protected page like `/settings` could land on
     `/login?next=/settings` instead of `/` — a confusing thing to see
     right after asking to sign out. Fixed with a hard navigation
     (`window.location.href`) instead of a client-side push.
  3. **Mobile nav gap**: at 320px the nav's link list was `hidden
     md:flex` with no mobile alternative — Home/Discover/My Cats/
     Profile were unreachable except via the small avatar icon. Fixed
     with a hamburger menu, verified interactively (menu opens, links
     actually navigate).

## What Does Not Exist Yet

Image generation (Phase 13), advanced analytics, a mobile app, a
social feed, chat, OAuth login, Redis-backed rate limiting (the
abstraction is in place, the implementation is still in-memory), and
S3-compatible image storage (the `ImageStorageProvider` interface is
ready, only the local-disk implementation exists). See ROADMAP.md
Phases 10–17.

## Known Limitations / Honest Gaps

- **Rate limiting is still in-memory, single-process** — unchanged
  from Phase 6, now behind a swappable `RateLimiter` Protocol so a
  Redis implementation is additive, not a rewrite.
- **Image storage is local-disk only** — `LocalImageStorageProvider`
  writes to a configurable directory served via `/media`; the
  `ImageStorageProvider` ABC is shaped for S3 but no cloud
  implementation exists yet.
- **Demo (offline, no `ANTHROPIC_API_KEY`) analyses persist the same
  as real ones** — the demo/real distinction is about the *content*
  (`profile_mode`/`story_mode: "demo"`), not about whether the row is
  saved; this is unchanged behavior from Phase 7/8, documented rather
  than silently relied upon.
- **Client-side route protection only** (`RequireAuth` wrapper), not
  server-side/middleware — matches the codebase's established
  all-client-component pattern; accepted tradeoff is a brief
  loading-state flash before redirect, never actual data exposure
  (every private endpoint is independently ownership-checked on the
  backend regardless of what the frontend renders).
- **One unavoidable browser-console 401 per guest page load**: an
  httpOnly cookie can't be checked client-side before asking the
  server, so `GET /api/v1/auth/me` always 401s once for a guest and
  the browser logs it as a failed network request — this is
  architectural, not a bug, and does not affect the app's actual
  zero-JS-error bar.
- **No live Anthropic API call tested** — unchanged gap from Phases 6–8.
- **Local dev Postgres on host port 5433** — unchanged from Phase 7.
- **Docker gap unchanged from Phase 4/5**: the backend image doesn't
  install `requirements-ml.txt`, so breed/color analysis stay
  demo-mode in containers.
- **`vitest.config.ts` uses `pool: "threads"`** — unchanged from
  Phase 7 (Windows + OneDrive-synced-path-with-a-space environment
  quirk).

## Next Steps

Begin Phase 10. Candidates per ROADMAP.md: deeper collection features
(bulk actions, pagination polish), a real image-generation provider
for the Wallpaper button (Phase 13 groundwork), or OAuth login —
nothing beyond Phase 9's explicit scope has been started.

## Notes for Future Sessions

- **`passlib[bcrypt]==1.7.4` is broken against `bcrypt==5.0.0`**
  (`AttributeError: module 'bcrypt' has no attribute '__about__'`),
  confirmed empirically, not assumed. Use `bcrypt` directly.
- **DB-backed opaque session tokens beat JWT here** specifically
  because logout needs to be immediate and real (a DB row delete) —
  a stateless JWT can't be revoked without extra machinery. Full
  rationale in ARCHITECTURE.md §11.
- **Ownership must be enforced in the repository query itself**
  (`WHERE user_id = :user_id`), not as a check bolted onto the route
  handler afterward — the latter is one missed `if` away from a
  cross-user data leak; the former makes it structurally impossible.
- **A converter function's "is this the owner's view" flag should
  never have a default** — the Phase 9 privacy bug (see above) existed
  specifically because `owned: bool = False` let call sites forget to
  pass it explicitly. A required kwarg turns "forgot to think about
  this" into a type error.
- **`useSearchParams()` requires a `<Suspense>` boundary** for Next.js
  16 static prerendering, discovered building `/login`/`/register`.
- **Hard navigation (`window.location.href`), not `router.push`, for
  logout** — sidesteps a real race against `RequireAuth`'s
  redirect-to-login effect. See the logout bug above.
- Previously noted lessons (Base UI quirks, dark-mode media-query
  strategy, forced-tool-use for structured LLM output, the
  `useSyncExternalStore` pattern for SSR-safe external state, the
  ref-returned-from-a-hook React Compiler lint gotcha, the
  self-referential `--font-sans` bug, `Badge`'s `whitespace-nowrap`
  footgun) all still apply.
</content>
</invoke>
