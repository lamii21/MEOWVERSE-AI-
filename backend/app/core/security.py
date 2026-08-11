import hashlib
import secrets

import bcrypt

# passlib[bcrypt]==1.7.4 (pre-staged since Phase 1) is incompatible with
# bcrypt>=4.1 — its version-detection shim reads an attribute
# (`bcrypt.__about__`) that modern bcrypt no longer exposes, and its
# fallback bug-detection path also breaks on bcrypt 5.x's changed error
# message. Confirmed broken against this project's actual installed
# versions (passlib 1.7.4 + bcrypt 5.0.0) before writing this module —
# not a hypothetical. Using the `bcrypt` library directly instead:
# simpler, actively maintained, no compatibility shim to break.
_BCRYPT_MAX_PASSWORD_BYTES = 72  # bcrypt silently ignores bytes beyond this


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password is too long.")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        # Malformed hash — never let a corrupt DB value crash the login
        # attempt into a 500; it should just fail to verify.
        return False


def generate_session_token() -> str:
    """A cryptographically random, unguessable opaque token — 256 bits
    of entropy, URL-safe. This is what goes in the cookie."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """What's actually stored in the `sessions` table. SHA-256 (not
    bcrypt) is deliberate and correct here: unlike a password, this
    token already has 256 bits of real entropy and was never meant to
    be memorable/guessable in the first place, so it needs no slow,
    salted KDF — a fast cryptographic hash is exactly right, and lets
    session lookups stay a single indexed equality query instead of
    bcrypt's expensive per-attempt hashing.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
