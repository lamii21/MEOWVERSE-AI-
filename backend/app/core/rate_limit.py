import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

_WINDOW_SECONDS = 60.0

# In-memory, per-process, per-client-IP fixed window. Fine for a
# pre-auth, single-instance deployment; move to a shared store (Redis)
# once Phase 9 adds auth and multi-instance deployment is on the table.
_request_log: dict[str, deque[float]] = defaultdict(deque)


def _client_id(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    client_id = _client_id(request)
    now = time.monotonic()

    window = _request_log[client_id]
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail="Too many requests — please slow down and try again in a moment.",
        )

    window.append(now)


def reset_rate_limits() -> None:
    """Test-only helper — clears in-memory state between test cases."""
    _request_log.clear()
