import logging
import sys


def configure_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s :: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Never let third-party libraries log request bodies / secrets at INFO.
    # httpx/httpcore carry the actual HTTP requests (including the
    # Anthropic/OpenAI clients' auth headers); each SDK's own logger can
    # also echo request/response payloads at DEBUG. None of them should
    # run below WARNING regardless of the app's own debug setting.
    #
    # Phase 16 finding: `openai` (added in Phase 14) uses its own
    # logger tree (`openai._base_client`, a child of `"openai"`) — a
    # separate namespace from `httpx`/`httpcore`, exactly like
    # `anthropic`'s — that was never added here, so with this app's
    # `debug=True` default it would inherit DEBUG from the root logger
    # and could log request/response details. Fixed by suppressing it
    # the same way `anthropic` already is.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
