"""Crawl-detected issue kind. Split out of `schema/enums.py` to keep that
module under the 300-line cap (AT-600) -- re-exported from enums.py so every
existing `from autotester.schema.enums import IssueKind` still resolves.
"""

from __future__ import annotations

from enum import StrEnum


class IssueKind(StrEnum):
    """What kind of problem a crawl-detected `CrawlIssue` is."""

    CONSOLE = "console"
    NETWORK = "network"
    NAVIGATION = "navigation"
    DIALOG = "dialog"
    OVERLAY = "overlay"
    """A screen whose controls were covered by an in-page overlay (AT-227).
    A PRODUCT observation, not a tool failure: the screen really was
    uninteractable in the state the crawl met it, and saying so is the
    difference between a blocked crawl and a crawl that looks complete."""

    EVIDENCE = "evidence"
    """The crawler itself failed to record something (AT-114). Kept distinct
    from the four kinds above because those describe the PRODUCT under test and
    this describes the tool: filing a tool failure as a product bug is exactly
    the dishonesty X9 forbids for third-party noise."""
