from fastapi import HTTPException, Request

from app.core.config import get_settings


async def verify_same_origin(request: Request) -> None:
    """CSRF defense for cookie-authenticated, state-changing endpoints.

    Primary defense is the session cookie's `SameSite=Lax` attribute
    (set in app/api/v1/auth.py) — modern browsers simply don't attach
    it to cross-site requests that aren't top-level navigations, which
    covers the classic "evil-site.com auto-submits a form/fetch to
    meowverse" CSRF case for the vast majority of real browsers.

    This dependency is defense-in-depth on top of that: it checks the
    `Origin` header (sent by browsers on essentially all fetch/XHR
    requests, same-origin or not) against the configured frontend
    origin(s), and 403s on a mismatch. It intentionally does NOT try to
    build a full double-submit-cookie CSRF token scheme — for a
    same-origin-by-configuration SPA+API pair with no cross-site form
    posting anywhere in the product, Origin-checking covers the actual
    threat model without the complexity (and the frontend-state
    bookkeeping) a token scheme would add.

    Applied to endpoints that use the ambient session cookie to *act*
    (logout, favorite, save, share) — not to login/register, which
    don't rely on pre-existing auth to do something.
    """
    origin = request.headers.get("origin")
    if origin is None:
        # No Origin header at all — same-origin navigations and most
        # non-browser clients (curl, server-to-server, Playwright
        # `request` context) don't send one. Requiring it would break
        # legitimate same-origin usage; the SameSite cookie is still
        # the primary defense either way.
        return

    if origin not in get_settings().cors_origins:
        raise HTTPException(status_code=403, detail="Cross-origin request blocked.")
