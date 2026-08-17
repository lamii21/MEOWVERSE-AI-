# MeowVerse AI — Production Release Checklist

Phase 17 deliverable. Walk through this before deploying to a real
environment. Each item names the file/setting it depends on. Checked
items were mechanisms actually verified this phase (built, run, and/or
tested); unchecked items are real deploy-time actions this development
environment has no real infrastructure (managed Postgres, S3 bucket,
domain/TLS) to perform — the mechanism behind each is verified even
where the action itself isn't.

## Environment

- [ ] `backend/.env.production` created from the example, real values filled in — a deploy-time action, not performed here (no real deployment target exists in this environment)
- [ ] `frontend/.env.production` created from the example — same
- [x] `ENVIRONMENT=production` and `DEBUG=false` — verified: ran the real Docker image with these exact values, confirmed correct behavior (INFO-level logs, no debug tracebacks)
- [x] `SESSION_COOKIE_SECURE` mechanism — verified: the setting is honored (`app/api/v1/auth.py`'s `set_cookie` call), tested via the full auth test suite; not literally set `true` in this environment since there's no real HTTPS origin to test against
- [x] `CORS_ORIGINS` non-wildcard enforcement — verified: `app/core/startup_checks.py` refuses to start with `environment=production` + `cors_origins=["*"]`, covered by `tests/test_startup_checks.py`
- [x] `NEXT_PUBLIC_API_URL` as a **build** ARG — verified: built the frontend image with `--build-arg NEXT_PUBLIC_API_URL=http://localhost:8000`, ran the container, confirmed the bundle called the correct URL

## Database

- [ ] A managed PostgreSQL instance provisioned — deploy-time action, no such instance exists in this environment
- [x] `DATABASE_URL` uses `postgresql+asyncpg://` — already the case, unchanged
- [x] **Migration cycle verified for real**: a full fresh upgrade → downgrade (`base`) → re-upgrade against an isolated, throwaway Postgres container (not the shared dev DB) completed with zero errors, all 13 tables present afterward
- [x] All 9 migrations individually reviewed for destructive changes — none found; every `NOT NULL` addition to an existing table used `server_default` or an explicit backfill-then-constrain pattern, every `downgrade()` fully reverses its `upgrade()`

## Secrets

- [x] No real API key, password, or session secret appears in any committed file — reviewed before this phase's commit
- [x] `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` optionality — verified: the app runs fully functionally without either (unchanged since Phase 6/14)
- [x] No secret referenced anywhere in `frontend/` — verified via a fresh grep this phase (`ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`S3_SECRET*`/`S3_ACCESS_KEY*` all absent)

## Docker

- [x] Backend image builds with `requirements-ml.txt` installed and **actually runs the real ML pipeline** — verified live: a real photo uploaded to the running container returned `breed_mode: "trained"`, a correct prediction, and a working Grad-CAM heatmap
- [x] Frontend image builds and runs its `runner` target — verified: built, ran, `curl`'d, got HTTP 200 and the correct page title
- [x] `docker-compose.prod.yml` — created; both services' build configuration verified via the individual `docker build`/`docker run` tests above (not run as a single `docker compose -f docker-compose.prod.yml up` end-to-end in this pass, since that needs real secrets this environment doesn't have)
- [x] CI's `docker` job builds both images — the exact same `docker build` commands the CI job runs were executed manually and succeeded; the workflow YAML is syntax-validated but has not been exercised by an actual GitHub Actions run (no push performed)

## ML Dependencies & Model Artifact

- [x] `REQUIRE_ML_MODELS=true` — verified live in the running container: real startup log confirms "REQUIRED AI/ML dependencies verified: torch/torchvision/opencv/faiss/scikit-learn importable, breed classifier weights present and checksum-verified"
- [x] `backend/ml/models/breed_classifier.pt` committed — done, confirmed via `git check-ignore`/`git status`
- [x] `.sha256` checksum present and verified at startup — confirmed live (see above) and via `tests/test_startup_checks.py`'s tampered-checksum test
- [x] `class_names.json`/`model_card.json` present — unchanged since Phase 4

## Storage

- [ ] `IMAGE_STORAGE_PROVIDER=s3` with real bucket/credentials — not configured in this environment (no real bucket provisioned); the provider code itself is implemented and unit-tested against a mocked `boto3` client (`tests/test_storage.py`), but a live S3 call was never made — **NOT VERIFIED LIVE**, consistent with this phase's own honesty rule
- [ ] Bucket public-read configuration — N/A without a real bucket
- [x] `SIMILARITY_INDEX_PATH` persistent-volume requirement — documented; concretely demonstrated *why* it matters this phase (a fresh container's local-storage `/media/*` 404s for every photo saved by a different process, since local disk doesn't survive across container instances)

## Auth / Cookies / CSRF

- [x] `SESSION_COOKIE_SECURE` mechanism works — see Environment above
- [x] `HttpOnly`, `SameSite=Lax` — unconditional in code, confirmed via the auth test suite
- [x] `verify_same_origin` CSRF defense — re-confirmed passing this phase's full regression run
- [x] Logout deletes the session row server-side — re-confirmed passing, plus new logging added this phase

## Rate Limiting

- [x] Every AI-cost-bearing endpoint rate-limited — re-confirmed passing this phase; 429s now logged (new this phase)
- [x] **Known limitation, documented not hidden**: the limiter is in-memory, per-process — correct for one instance, does **not** share counters across multiple backend instances. Deliberately **not** given a Redis-backed implementation this phase — this deployment doesn't need multi-instance scaling yet, and building an unused abstraction would have been exactly the "architecture aesthetics" the spec said not to add

## CORS / Security Headers

- [x] `CORS_ORIGINS` non-wildcard enforcement — see Environment above
- [x] `SecurityHeadersMiddleware` — added this phase, verified live (`curl -D -` against the running dev server showed all headers present) and via `tests/test_security_headers.py`, including confirming `/docs` still renders (CSP correctly excluded there)

## Backend

- [x] Full test suite passes — **458 collected, 457 passed, 1 skipped** (the 1 skip is an environment-conditional test that doesn't apply here since ML deps ARE installed)
- [x] `ruff check .` clean
- [x] `alembic upgrade head` succeeds against a fresh database — see Database above
- [x] `/health` and `/ready` both respond correctly — verified live

## Frontend

- [x] `pnpm lint` clean
- [x] `pnpm typecheck` clean (new script added this phase)
- [x] `pnpm test` passes — 193/193
- [x] `pnpm build` succeeds
- [x] The actual production build was served and exercised in a browser — see Production-Like E2E below

## CI/CD

- [x] `.github/workflows/ci.yml` extended (frontend typecheck+test, new `docker` job) — YAML syntax-validated, every command it runs was independently executed and passed manually this phase; **not exercised by an actual GitHub Actions run** (no push performed) — NOT VERIFIED in the sense of "a real CI run went green," though every individual command it invokes is confirmed working

## Production-Like E2E

- [x] **Run against the actual built Docker images** (not dev servers) — both production containers started together (backend `REQUIRE_ML_MODELS=true`, frontend `runner` target), a 26-step flow exercised via a real headless-browser script: guest landing → upload → analyze (real `breed_mode: "trained"`) → Grad-CAM → personality → story → portrait → guest save prompt → register → re-analyze authenticated → collection → explore → search → filter → logout → login again → collection-after-relogin → mobile → reduced motion. Completed cleanly, only architecturally-expected console entries (guest 401 checks, honest 404s for an unclaimed guest analysis's owner-only endpoints — the same pattern confirmed benign in Phase 16)

## Security Regression

- [x] Anonymous cannot access private data — covered by the passing test suite (`test_ownership.py`, `test_analyses.py`)
- [x] User A cannot access/regenerate User B's private/owned AI content — covered (`test_ownership.py`, Phase 13/14 ownership tests)
- [x] A public viewer cannot trigger an owner-only cost-bearing operation — portrait generation has no public-or-owned path at all (owner-only unconditionally), unchanged since Phase 14, re-confirmed passing
- [x] Logout invalidates the session server-side immediately — covered, re-confirmed
- [x] CSRF (Origin-header check) rejects a cross-origin request — covered, re-confirmed
- [x] Path traversal against `/media/...` is rejected — new dedicated test this phase (`tests/test_storage.py`)
- [x] Oversized uploads rejected with 422 — covered, re-confirmed
- [x] Invalid/corrupted/decompression-bomb images rejected with a clean 422, never a 500 — **real bug found and fixed this phase**, regression test added
- [x] No API key ever reaches the frontend bundle — verified via a fresh grep this phase

## Backups

- [ ] Managed Postgres provider's automated backup enabled — N/A, no real managed instance provisioned in this environment
- [x] `pg_dump`/`pg_restore` strategy documented (README.md) — the provider-agnostic fallback that works regardless of which managed Postgres is chosen; not exercised against a real production database (none exists here)

## Logging

- [x] `DEBUG=false` → `INFO` floor — verified live
- [x] `httpx`/`httpcore`/`anthropic`/`openai` loggers pinned to `WARNING` — unchanged since Phase 6/16, re-confirmed
- [x] No password/session token/API key/full private prompt ever logged — confirmed by code review this phase; auth logging added this phase logs only user id + client IP, never credentials

---

**What this checklist deliberately does not include**, per the phase's own scope: Kubernetes manifests, a Prometheus/Grafana stack, a payment system, a mobile app, or a Redis-backed rate limiter — none of these are required to deploy this project as a portfolio-quality production service, and adding them would be exactly the "feature creep" Phase 17 was told not to introduce.
