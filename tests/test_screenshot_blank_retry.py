"""T-136 grade-fix G4: a uniform / near-blank screenshot is recaptured, bounded, and recorded.

Live defect (run-01M582T0GEWYH561PHSV8JANPX): the frame taken right after a Login click was
a uniform blank page (std 0) in 1 of 2 identical runs. BrowserSession.screenshot now waits for
load state / network idle and recaptures (at most BLANK_RETRIES times); if the frame is still
blank it records that as a DOM evidence row. Contract: browser-and-secrets.md B5-B9. Offline.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
from test_browser_settle import session_with_fake_page

from autotester.browser import evidence
from autotester.schema.enums import EvidenceKind


class ShotPage:
    """A page whose Nth screenshot is blank or not, and which counts load-state waits."""

    def __init__(self, frames: list[str]) -> None:
        self.frames = frames
        self.shots = 0
        self.waits: list[str] = []
        self.url = "https://app.pathlynks.test/login"

    def add_style_tag(self, content: str = "") -> None:
        pass

    def wait_for_load_state(self, state: str = "load", timeout: int = 0) -> None:
        self.waits.append(state)

    def wait_for_timeout(self, timeout_ms: int) -> None:
        pass

    def screenshot(self, path: str, full_page: bool = False, **_: object) -> None:
        kind = self.frames[min(self.shots, len(self.frames) - 1)]
        self.shots += 1
        if kind == "blank":
            Image.new("RGB", (80, 50), (248, 248, 248)).save(path)
        elif kind == "notimage":
            Path(path).write_bytes(b"not a png")
        else:
            image = Image.new("RGB", (80, 50), "white")
            ImageDraw.Draw(image).rectangle((5, 5, 40, 20), fill="black")
            image.save(path)


def _session(tmp_path: Path, frames: list[str]):
    session = session_with_fake_page(tmp_path)
    session._page = ShotPage(frames)
    return session, session._page


def test_g4_blank_frame_is_recaptured_after_waiting_for_network_idle(tmp_path) -> None:
    session, page = _session(tmp_path, ["blank", "content"])
    ev = session.screenshot("step04-click", step_order=4)
    assert page.shots == 2
    assert "networkidle" in page.waits
    with Image.open(session.state.run_dir / ev.path) as final:
        lo, hi = final.convert("L").getextrema()
    assert hi - lo > 3, "the kept frame is the recaptured, non-blank one"
    assert not [e for e in session.state.evidence if e.kind is EvidenceKind.DOM]


def test_g4_a_good_first_frame_is_not_retried(tmp_path) -> None:
    session, page = _session(tmp_path, ["content"])
    session.screenshot("step01-navigate", step_order=1)
    assert page.shots == 1 and page.waits == []


def test_g4_retries_are_bounded_and_a_still_blank_frame_is_recorded(tmp_path) -> None:
    session, page = _session(tmp_path, ["blank"])
    session.screenshot("step04-click", step_order=4)
    assert page.shots == 1 + evidence.BLANK_RETRIES
    rows = [e.path for e in session.state.evidence if e.kind is EvidenceKind.DOM]
    assert len(rows) == 1 and "blank" in rows[0] and "step04-click.png" in rows[0]
    assert rows[0].startswith("screenshot blank"), "must not look like an `assert ` row"


def test_g4_an_unreadable_frame_is_not_treated_as_blank(tmp_path) -> None:
    session, page = _session(tmp_path, ["notimage"])
    session.screenshot("step02-fill", step_order=2)
    assert page.shots == 1
