"""Screenshot capture and evidence-recording for `BrowserSession`.

Split out of `browser/session.py` (AT-567 -- the file sat at the C2 300-line
cap with no headroom) into its own mixin: the masking CSS (B7), the AT-036
transient-CDP-race retry, the AT-572/AT-577 per-case `evidence_prefix`
nesting, and the redact-then-append trail every action writes to `SessionState
.evidence` are one concern, distinct from the lifecycle and page-action
methods that stay in `session.py`. `BrowserSession` inherits `EvidenceMixin`
so both `screenshot()` and `_record()` keep behaving as ordinary methods on
`self` (`self.page`, `self.state`, `self.secrets` -- all still defined on
`BrowserSession.__init__`).
"""

from __future__ import annotations

from autotester.schema.enums import EvidenceKind
from autotester.schema.run import Evidence

# CSS applied to secret inputs right before capture. Text becomes unreadable
# without changing layout, so the screenshot still shows *where* the field is.
MASK_CSS = (
    "[data-autotester-secret] { -webkit-text-security: disc !important; "
    "color: transparent !important; text-shadow: 0 0 8px rgba(0,0,0,.6) !important; }"
)
MASK_ATTR = "data-autotester-secret"


class EvidenceMixin:
    """`screenshot()` and `_record()` -- mixed into `BrowserSession`."""

    def screenshot(self, label: str, *, step_order: int | None = None) -> Evidence:
        """Capture with every secret input masked first (B7). AT-036: under
        Xvfb, `Page.screenshot` intermittently raises a transient CDP
        compositor race right after a DOM update — one retry after a short
        wait resolves it; a second consecutive failure is real and
        propagates (full history: execute.md's amendment log). AT-572/AT-577:
        nests under `evidence_prefix` when set, so sibling cases sharing
        `run_dir` never collide."""
        self.page.add_style_tag(content=MASK_CSS)
        self.state.screenshots += 1
        name = f"{self.state.screenshots:02d}-{label}.png"
        rel = f"{self.state.evidence_prefix}/{name}" if self.state.evidence_prefix else name
        full = self.state.run_dir / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        path = str(full)
        try:
            self.page.screenshot(path=path, full_page=False)
        except Exception as exc:
            if "captureScreenshot" not in str(exc):
                raise
            self.page.wait_for_timeout(250)
            self.page.screenshot(path=path, full_page=False)
        return self._record(EvidenceKind.SCREENSHOT, rel, step_order=step_order, label=label)

    # -- evidence ---------------------------------------------------------------
    def _record(self, kind: EvidenceKind, path: str, *, step_order: int | None = None,
                label: str | None = None) -> Evidence:
        scrubbed = self.secrets.redactor().scrub(path)
        item = Evidence(kind=kind, path=scrubbed, step_order=step_order, label=label, masked=True)
        self.state.evidence.append(item)
        return item
