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
    # Anthropic client's auth header); anthropic's own logger can also
    # echo request/response payloads at DEBUG. None of them should run
    # below WARNING regardless of the app's own debug setting.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
