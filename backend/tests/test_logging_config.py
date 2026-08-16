"""Phase 16 regression test for a real, discovered bug: `configure_logging`
suppressed `anthropic`'s logger but not `openai`'s (added in Phase 14) —
a separate logger namespace from `httpx`/`httpcore`, so with this app's
`debug=True` default it would have inherited DEBUG and could log
request/response details, including headers. This test would have
caught the gap before the fix.
"""

import logging

from app.core.logging import configure_logging


def test_third_party_ai_sdk_loggers_are_never_below_warning():
    configure_logging(debug=True)  # the app's own default — the worst case for leakage

    for name in ("httpx", "httpcore", "anthropic", "openai"):
        assert logging.getLogger(name).level >= logging.WARNING, (
            f"{name}'s logger must never run below WARNING — it can carry "
            "request/response payloads, including auth headers, at DEBUG."
        )


def test_suppression_holds_even_when_app_debug_is_false():
    configure_logging(debug=False)

    for name in ("httpx", "httpcore", "anthropic", "openai"):
        assert logging.getLogger(name).level >= logging.WARNING
