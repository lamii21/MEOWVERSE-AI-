from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths that need to stay browser/CDN-friendly for FastAPI's built-in
# interactive docs (Swagger UI loads its JS/CSS from jsdelivr's CDN by
# default) — a strict CSP here would silently break the docs page
# rather than protect anything, since these routes serve no user data
# and take no request body.
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers to every response (Phase 17 §16).

    This is a JSON API (plus a `/media` static mount for cat photos, and
    FastAPI's own `/docs`/`/redoc`) — there is no server-rendered HTML
    that legitimately needs inline scripts/styles or third-party
    framing, so a strict default-deny CSP is safe everywhere except the
    docs routes, which are excluded rather than loosened globally.
    `Strict-Transport-Security` is safe to always send: browsers only
    honor it on a connection that is already HTTPS, so it's a no-op
    (not a bug) during local plain-HTTP development.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )

        return response
