import asyncio
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import engine as app_engine
from app.core.rate_limit import reset_rate_limits
from app.main import app

if sys.platform == "win32":
    # asyncpg + the default ProactorEventLoop have a known Windows-only
    # incompatibility: closing/rolling back a connection can race with
    # the proactor's socket transport being torn down, raising
    # `AttributeError: 'NoneType' object has no attribute 'send'` from
    # asyncio internals (not our code). The SelectorEventLoop doesn't
    # have this issue and doesn't cost us anything here — this test
    # suite doesn't need Proactor's subprocess support.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# A dedicated test engine with NullPool, deliberately NOT the app's
# module-level pooled engine (app.core.database.engine). The Windows
# teardown quirk above means a connection's close() can fail partway
# through; with the app's normal pool, that leaves a half-closed
# connection sitting in the pool for the *next* test to check out,
# which then fails with "another operation is in progress" —
# discovered by hitting it directly while building these tests.
# NullPool hands out a genuinely fresh connection every time, so one
# test's messy teardown can't poison the next test.
_test_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest.fixture
async def db_session():
    """A real AsyncSession against the local dev Postgres (see
    docker-compose.yml — port 5433 on the host). Tests that need actual
    persistence (Phase 7 story/analysis tests) use this directly rather
    than mocking the database, matching this project's "verify for
    real" approach to Postgres/Redis/ML throughout. Local test runs may
    accumulate rows across sessions (harmless, not asserted against);
    CI gets a fresh ephemeral Postgres container every run.
    """
    session = _test_session_factory()
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception:
            pass


@pytest.fixture
def client():
    """`TestClient` used as a context manager, not a bare module-level
    instance — Starlette only keeps ONE stable anyio portal (and so one
    stable event loop) alive for the `with` block's lifetime. A bare
    `TestClient(app)` can open a fresh portal per call, and since
    app.core.database's engine/pool is a module-level singleton shared
    across every test, a connection checked out under one call's loop
    being reused on a later call's (different) loop raises "Future
    attached to a different loop" — hit directly while building
    test_stories_api.py (the 2nd sequential request in a test would
    fail even though the 1st succeeded). This fixture plus
    `_fresh_app_engine_pool` below together make the loop this test's
    requests run on consistent, and the connection pool clean at the
    start of that loop.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
async def _fresh_app_engine_pool():
    """Disposes the app's shared connection pool before each test so
    whichever loop this test ends up using (see `client` fixture above)
    starts from an empty pool — no connection left over from a
    different test's (different) loop. See `client` fixture docstring
    for the full story; this was a real bug found and fixed while
    building the Phase 7 story-endpoint tests.
    """
    await app_engine.dispose()
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    """Shared across every test file that hits a rate-limited endpoint
    (POST /api/v1/analyses, POST /api/v1/analyses/{id}/story) via
    TestClient — without this, request counts would leak between test
    functions and between files."""
    reset_rate_limits()
    yield
    reset_rate_limits()
