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

from pathlib import Path

from autotester.browser import assertions
from autotester.schema.enums import EvidenceKind
from autotester.schema.run import Evidence
from autotester.stages.run_budget import RunBudgetExceeded

# CSS applied to secret inputs right before capture. Text becomes unreadable
# without changing layout, so the screenshot still shows *where* the field is.
MASK_CSS = (
    "[data-autotester-secret] { -webkit-text-security: disc !important; "
    "color: transparent !important; text-shadow: 0 0 8px rgba(0,0,0,.6) !important; }"
)
MASK_ATTR = "data-autotester-secret"
# T-136 G4: a frame taken before the post-click page rendered is one flat colour. Recapture at most
# BLANK_RETRIES times, each after a bounded network-idle wait (<= ~2 s per try, ~6 s in all).
BLANK_RETRIES = 3
BLANK_IDLE_MS = 1500
BLANK_GRACE_MS = 300
BLANK_SPREAD = 3  # max-min luminance at or below this counts as uniform


def _is_blank(path: str) -> bool:
    """True when the PNG at `path` is one flat colour; an unreadable file is NOT blank."""
    try:
        from PIL import Image

        with Image.open(path) as image:
            low, high = image.convert("L").getextrema()
    except Exception:
        return False
    return high - low <= BLANK_SPREAD


class EvidenceMixin:
    """`screenshot()` and `_record()` -- mixed into `BrowserSession`."""

    def _field_sample(self, target, locator: str, *, secret: bool) -> str:
        """One bounded observation; never read known or unclassified secret values."""
        assertions._probe(self)
        if secret or locator in self.state.secret_locators:
            return "[secret]"
        try:
            kind = target.get_attribute("type", **self._timeout())
            self._timeout()
            masked = target.get_attribute(MASK_ATTR, **self._timeout())
            self._timeout()
            if str(kind).lower() == "password" or masked is not None:
                return "[secret]"
            is_input = target.evaluate(
                "el => ['INPUT', 'TEXTAREA'].includes(el.tagName)", **self._timeout())
            self._timeout()
            if is_input is not True:
                return "unavailable"
            value = target.input_value(**self._timeout())
            self._timeout()
            return (repr(self.secrets.redactor().scrub(value))
                    if isinstance(value, str) else "unavailable")
        except RunBudgetExceeded:
            raise
        except Exception:
            self._timeout()
            return "unavailable"

    def screenshot(self, label: str, *, step_order: int | None = None) -> Evidence:
        """Capture with every secret input masked first (B7). AT-036: under
        Xvfb, `Page.screenshot` intermittently raises a transient CDP
        compositor race right after a DOM update — one retry after a short
        wait resolves it; a second consecutive failure is real and
        propagates (full history: execute.md's amendment log). AT-572/AT-577:
        nests under `evidence_prefix` when set, so sibling cases sharing
        `run_dir` never collide."""
        self.page.add_style_tag(content=MASK_CSS)
        self._timeout()
        self.state.screenshots += 1
        name = f"{self.state.screenshots:02d}-{label}.png"
        rel = f"{self.state.evidence_prefix}/{name}" if self.state.evidence_prefix else name
        full = self.state.run_dir / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        path = str(full)
        try:
            self.page.screenshot(path=path, full_page=False, **self._timeout())
        except Exception as exc:
            if "captureScreenshot" not in str(exc):
                raise
            self.page.wait_for_timeout(self._timeout(250).get("timeout", 250))
            self.page.screenshot(path=path, full_page=False, **self._timeout())
        self._timeout()
        self._recapture_blank(path, rel, step_order)
        return self._record(EvidenceKind.SCREENSHOT, rel, step_order=step_order, label=label)

    def _recapture_blank(self, path: str, rel: str, step_order: int | None) -> None:
        """T-136 G4: a uniform frame is re-taken after load/network-idle, bounded; if it stays
        blank, say so in a DOM evidence row (not an `assert ` row) rather than hide it."""
        for _ in range(BLANK_RETRIES):
            if not _is_blank(path):
                return
            for state, ms in (("networkidle", BLANK_IDLE_MS), ("timeout", BLANK_GRACE_MS)):
                try:
                    if state == "timeout":
                        self.page.wait_for_timeout(self._timeout(ms).get("timeout", ms))
                    else:
                        self.page.wait_for_load_state(state, timeout=self._timeout(ms).get(
                            "timeout", ms))
                except RunBudgetExceeded:
                    raise
                except Exception:
                    pass
            self.page.screenshot(path=path, full_page=False, **self._timeout())
            self._timeout()
        if _is_blank(path):
            self._record(EvidenceKind.DOM, f"screenshot blank after {BLANK_RETRIES} recaptures: "
                         f"{Path(rel).name}", step_order=step_order)

    # -- evidence ---------------------------------------------------------------
    def _record(self, kind: EvidenceKind, path: str, *, step_order: int | None = None,
                label: str | None = None) -> Evidence:
        scrubbed = self.secrets.redactor().scrub(path)
        item = Evidence(kind=kind, path=scrubbed, step_order=step_order, label=label, masked=True)
        self.state.evidence.append(item)
        return item
