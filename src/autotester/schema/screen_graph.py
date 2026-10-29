"""What one page-visit observed: its interactive elements and identity inputs.

`ElementRef`/`PageObservation` are B1's minimal slice — `stages/explore.py`
(Track B3) and `stages/screen_identity.py` (B2) extend this file with
`ScreenNode`/`ScreenEdge`/`CrawlFrontier` once the crawl stage itself exists.
`browser/observe.py` is the only producer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotester.core.ids import content_id
from autotester.schema.base import Artifact
from autotester.schema.crawl_guidance import GuidanceAnnotation
from autotester.schema.enums import Action, EdgeOutcome, NodeStatus


class ElementRef(BaseModel):
    """One interactive element found by `browser/enumerate.js`."""

    model_config = ConfigDict(extra="forbid")

    role: str
    name: str = ""
    selector: str
    enabled: bool = True
    visible: bool = True
    obscured: bool = Field(
        default=False,
        description="CSS-visible but covered by something else (a modal veil, a "
        "sticky bar) -- unreachable to a human, so never a crawl candidate, and "
        "reported in an OVERLAY issue so a blocked screen is never silent (AT-227). "
        "Deliberately NOT used by screen identity: `stages/screen_identity.py::"
        "structural_signature` keys on `visible` alone, and its docstring says why "
        "(AT-338 -- this description asserted the opposite for one cycle)",
    )
    href: str | None = None
    is_form_submit: bool = False
    in_row: bool = Field(
        default=False,
        description="inside a table row / list item with siblings — excluded from a "
        "screen's structural signature so two list pages with different rows are one screen",
    )
    target_blank: bool = False
    tag: str = ""
    type: str = Field(
        default="",
        description="the `<input>`'s real type ('password', 'file', 'text', ...), lowercased; "
        "'' for any non-input and for a graph stored before AT-650. The typing gate "
        "(`stages/explore_safety.py::typing_target_allowed`) reads it, never the name alone",
    )
    field_label: str | None = Field(
        default=None, exclude=True,
        description="crawl-guidance G3: set by enumerate.js for a data-bearing form control only "
        "(aria-label / <label> / placeholder text, never the value or option text); '' = none. "
        "In memory only (exclude=True): never persisted, so crawl artifacts are unchanged",
    )


class ApiCall(BaseModel):
    """One successful first-party API request a screen made: method + path pattern + status.

    The path is `url_template`'d (ids collapse), query-less and host-less, so it is a stable
    key that can be compared against a reference endpoint map; `count` is how many times the
    crawl saw that exact (method, path, status) while on the screen."""

    model_config = ConfigDict(extra="forbid")

    method: str
    path: str
    status: int
    count: int = 1


class PageObservation(BaseModel):
    """One page-visit's raw material: its url/title and interactive elements."""

    model_config = ConfigDict(extra="forbid")

    url: str
    title: str = ""
    elements: list[ElementRef] = Field(default_factory=list)


class ScreenNode(Artifact):
    """One distinct screen the crawl found. Identity is structural
    (`stages/screen_identity.py::node_from`), never URL-only and never an
    LLM description — the two failure modes the prior attempt hit."""

    id: str = ""
    crawl_id: str
    project: str
    url_template: str
    url_example: str = Field(description="one real URL that produced this identity")
    signature: str = Field(description="content hash of the sorted (role, name) set")
    title: str = ""
    name: str = ""
    depth: int = 0
    status: NodeStatus = NodeStatus.QUEUED
    elements: list[ElementRef] = Field(default_factory=list)
    screenshot_ref: str | None = None
    console_errors: list[str] = Field(default_factory=list)
    failed_requests: list[str] = Field(default_factory=list)
    discovered_by: str | None = Field(default=None, description="the ScreenEdge.id that found it")
    guidance: list[GuidanceAnnotation] | None = Field(
        default=None, description="crawl-guidance (D-119): this screen's rankings, grafted onto "
        "PortalPersona.graph by the persona build")
    api_calls: list[ApiCall] = Field(
        default_factory=list,
        description="successful (status < 400) first-party XHR/fetch requests seen while on "
        "this screen, one row per (method, path pattern, status); [] on a node recorded before "
        "this field existed or one that made none",
    )

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            payload = {"t": self.url_template, "s": self.signature}
            object.__setattr__(self, "id", content_id("node", payload))


class ScreenEdge(Artifact):
    """One candidate action the crawl tried from one screen."""

    id: str = ""
    crawl_id: str
    from_node: str
    to_node: str | None = None
    action: Action
    target: str = Field(description="the element's selector")
    name: str = ""
    outcome: EdgeOutcome
    reason: str | None = None
    error_class: str | None = Field(
        default=None,
        description="for an `errored` edge: the exception class name (e.g. 'TimeoutError') or "
        "'ReturnLost'; `reason` then holds its redacted, single-line, bounded message",
    )

    def model_post_init(self, _context: object) -> None:
        if not self.id:
            payload = {
                "crawl_id": self.crawl_id, "from": self.from_node,
                "target": self.target, "action": str(self.action),
            }
            object.__setattr__(self, "id", content_id("edge", payload))


class CrawlFrontier(BaseModel):
    """The BFS queue state — persisted so a crash mid-crawl leaves a resumable
    (if not yet auto-resumed, per plan.md's no-fire list) partial graph."""

    model_config = ConfigDict(extra="forbid")

    queue: list[str] = Field(default_factory=list)
    visited: list[str] = Field(default_factory=list)
    actions_used: int = 0
    screens_found: int = 0
