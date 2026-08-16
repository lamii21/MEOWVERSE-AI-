import time
from collections import defaultdict, deque
from typing import Protocol

from fastapi import HTTPException, Request

from app.core.config import get_settings

_WINDOW_SECONDS = 60.0


class RateLimiter(Protocol):
    """Swappable interface (Phase 9) — `InMemoryRateLimiter` below is the
    only implementation today. A Redis-backed one (sorted set +
    ZREMRANGEBYSCORE/ZADD/ZCARD, or a Lua token bucket, keyed the same
    way) is a drop-in replacement for multi-instance deployment; nothing
    at the call sites (`enforce_rate_limit`/`enforce_auth_rate_limit`)
    would need to change, only which limiter instance they delegate to.
    """

    def check(self, key: str, limit_per_minute: int) -> bool:
        """Returns True if the request is allowed, False if over limit."""
        ...

    def reset(self) -> None:
        """Test-only: clear all state."""
        ...


class InMemoryRateLimiter:
    """In-memory, per-process, fixed 60s window — fine for a
    single-instance deployment, not correct across multiple instances
    (each process has its own counters)."""

    def __init__(self) -> None:
        self._log: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit_per_minute: int) -> bool:
        now = time.monotonic()
        window = self._log[key]
        while window and now - window[0] > _WINDOW_SECONDS:
            window.popleft()

        if len(window) >= limit_per_minute:
            return False

        window.append(now)
        return True

    def reset(self) -> None:
        self._log.clear()


_limiter: RateLimiter = InMemoryRateLimiter()


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    """Applied to the AI-calling endpoints (analyze, story generation)."""
    settings = get_settings()
    if not _limiter.check(_client_id(request), settings.rate_limit_per_minute):
        raise HTTPException(
            status_code=429,
            detail="Too many requests — please slow down and try again in a moment.",
        )


async def enforce_portrait_rate_limit(request: Request) -> None:
    """Applied to POST /api/v1/analyses/{id}/portraits specifically
    (Phase 14 spec §24) — a real image generation call is meaningfully
    more expensive than the text-completion endpoints `enforce_rate_limit`
    covers, so it gets its own, tighter budget and its own key prefix
    (a burst of portrait generations from one IP doesn't also exhaust
    that IP's analyze/story budget, or vice versa). Enforced server-side
    only — the frontend disabling its Generate button is UX, not the
    actual control (spec §24: "do not rely on frontend button
    disabling").
    """
    settings = get_settings()
    if not _limiter.check(
        f"portrait:{_client_id(request)}", settings.portrait_generation_rate_limit_per_minute
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many portraits requested — please slow down and try again in a moment.",
        )


async def enforce_explore_rate_limit(request: Request) -> None:
    """Applied to the `/explore/*` browsing endpoints (Phase 15 spec
    §29) — deliberately looser than `enforce_rate_limit`, its own key
    prefix so a burst of browsing never eats into an IP's AI-endpoint
    budget or vice versa. A single `/explore` page view fires several
    parallel section requests plus one more per filter/search
    interaction, none of which carry any AI cost — sharing the
    AI-endpoint limit was confirmed, via a real Playwright E2E run, to
    trip false-positive 429s during completely ordinary browsing.
    """
    settings = get_settings()
    if not _limiter.check(
        f"explore:{_client_id(request)}", settings.explore_rate_limit_per_minute
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many requests — please slow down and try again in a moment.",
        )


async def enforce_auth_rate_limit(request: Request) -> None:
    """Applied to register/login specifically — a tighter limit than
    the general API, since brute-forcing passwords / spamming account
    creation is a different threat model. Keyed separately from
    `enforce_rate_limit` (own prefix) so a burst of login attempts from
    one IP doesn't also exhaust that IP's analyze-endpoint budget, or
    vice versa.
    """
    settings = get_settings()
    if not _limiter.check(f"auth:{_client_id(request)}", settings.auth_rate_limit_per_minute):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts — please slow down and try again in a moment.",
        )


def reset_rate_limits() -> None:
    """Test-only helper — clears in-memory state between test cases."""
    _limiter.reset()
