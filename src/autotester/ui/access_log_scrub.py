"""Scrub the uvicorn access log of query strings and `/v/<token>` path tokens (AT-1390).

D-107 keeps uvicorn's access log on in `docker/entrypoint.sh`; each line carries the request
target, so a login `next=` and a share-link token would reach the container log. A
`logging.Filter` on the `uvicorn.access` logger rewrites the target before any handler sees it,
so it holds however uvicorn is launched. Method, status and the rest of the path stay readable.
Whole-query masking is a different rule from `core.redact.scrub_url_credentials` (which masks only
credential-named parameters), so this module does not reuse it. Contract: qa/contracts/auth.md AU22.
"""

from __future__ import annotations

import logging
import re

__all__ = ["AccessLogScrub", "install_access_log_scrub", "scrub_target"]

_LOGGER = "uvicorn.access"
_TOKEN_SEGMENT = re.compile(r"/v/[^/?#]+")
_TARGET_ARG = 2  # uvicorn: '%s - "%s %s HTTP/%s" %d' % (client, method, target, version, status)


def scrub_target(target: str) -> str:
    """`/v/<token>/x?a=b` -> `/v/<redacted>/x?<redacted>`."""
    path, sep, _query = target.partition("?")
    path = _TOKEN_SEGMENT.sub("/v/<redacted>", path)
    return f"{path}?<redacted>" if sep else path


class AccessLogScrub(logging.Filter):
    """Rewrites the request target of every uvicorn access record; never drops a record."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) > _TARGET_ARG:
            target = args[_TARGET_ARG]
            if isinstance(target, str):
                clean = scrub_target(target)
                record.args = (*args[:_TARGET_ARG], clean, *args[_TARGET_ARG + 1:])
        return True


def install_access_log_scrub() -> None:
    """Attach the filter to `uvicorn.access` once (a repeat import adds no copy)."""
    logger = logging.getLogger(_LOGGER)
    if not any(isinstance(f, AccessLogScrub) for f in logger.filters):
        logger.addFilter(AccessLogScrub())
