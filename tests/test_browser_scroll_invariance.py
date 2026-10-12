"""One property, generated shapes: scrolling must not change WHAT is reported.

AT-423. Five separate defects in `visual_order.js` — AT-373, AT-379, AT-392,
AT-408, AT-416 — were all the same mistake, and all five were found by a checker
driving a browser at a shape the maker had no fixture for. Across three fix
cycles every command the manifests listed stayed green while a real false
negative shipped each time: the suite, ruff, doctor, and the mutation specs.

The five share one property:

    the multiset of glyphs `visual_text` reports must not change when the window
    or ANY scrollable container is scrolled anywhere in its range.

A reader can scroll. Anything a scroll can bring into view is text a reader can
see, so a detector claiming to report what a reader sees cannot report a
different set before and after. Every one of the five was a scroll-invariance
failure; AT-379 was literally filed as `equal_before_after=False`.

Two deliberate choices:

**The scrolls are PERFORMED, not computed.** Computing offsets from
`getBoundingClientRect` is exactly the reasoning that got this wrong five times
in a row. This drives the browser and compares what came back.

**The shapes are GENERATED, not imagined.** `tests/fixtures/bidi_site/
scrolled_panes.html` already *is* the AT-416 shape — `overflow:hidden` wrapping
`overflow:auto` — and cannot exhibit the defect only because the inner box does
not overflow. The shape was on screen and the one parameterisation chosen proved
the opposite property. Enumerating the product removes the need for anyone to
guess which corner is the dangerous one.

**Honest limit: the property is ONE-SIDED.** A detector that reported every node
on the page would be perfectly scroll-invariant. It says nothing about false
positives, so it is a floor beneath the "text a reader cannot see is not
reported" assertions in `test_browser_unreadable.py`, never a replacement.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from pathlib import Path

import pytest

from autotester.browser.observe import visual_text

OVERFLOWS = ("auto", "hidden")
DEPTHS = (1, 2, 3)


def _shapes() -> list[tuple[str, ...]]:
    """Every nesting of `overflow` values up to three deep.

    `visible` is left out on purpose: a box that does not clip cannot scroll
    either, so it adds pages without adding a state the detector treats
    differently. `scroll` behaves as `auto` once the content overflows, which it
    always does here by construction.
    """
    return [combo for depth in DEPTHS for combo in itertools.product(OVERFLOWS, repeat=depth)]


def _html(shape: tuple[str, ...], *, clip_path: bool, tall_page: bool) -> str:
    """Nested boxes, innermost holding two lines far enough apart to overflow.

    Every level gets an id so the driver can scroll it by name, and a spacer
    below the child so every level's own content overflows its 40px box — a
    level that cannot scroll cannot contribute the offset this is about.
    """
    body = ('<p>INNER_TOP</p>\n'
            '<p style="margin-top:300px">INNER_BOTTOM</p>')
    for level, overflow in enumerate(reversed(shape)):
        clip = "clip-path:inset(0 0 0 0);" if clip_path and level == len(shape) - 1 else ""
        body = (f'<div id="L{len(shape) - 1 - level}" '
                f'style="height:40px;width:300px;overflow:{overflow};{clip}">\n'
                f"{body}\n"
                '<div style="height:300px"></div>\n'
                "</div>")
    spacer = '<div style="height:2000px"></div>' if tall_page else ""
    return ("<!doctype html>\n<meta charset=\"utf-8\">\n<title>shape</title>\n"
            "<p>CONTROL_QUARTERLY_REPORT</p>\n"
            f"{body}\n{spacer}\n<p>PAGE_FOOT</p>\n")


def _label(shape: tuple[str, ...], clip_path: bool, tall_page: bool) -> str:
    return "-".join(shape) + ("+clip" if clip_path else "") + ("+tall" if tall_page else "")


CORPUS = [
    (_label(shape, clip_path, tall), shape, clip_path, tall)
    for shape in _shapes()
    for clip_path in (False, True)
    for tall in (False, True)
    # AT-426: an all-`hidden` shape on a SHORT page has nothing a reader can scroll
    # — no scrollable box, and a window that does not move. Six such pages sat in
    # the first corpus passing vacuously, uncaught by any mutation. They are left
    # out rather than counted as coverage.
    if "auto" in shape or tall
]

def _open_defects(shape: tuple[str, ...], clip_path: bool) -> list[str]:
    """Which open defects a shape exercises, derived from its STRUCTURE.

    AT-425. The first version measured WHICH shapes fail and then guessed WHY
    with `"AT-417" if "+clip" in label else "AT-416"` — wrong for 10 of 32, so
    the claim "option A flips 10" was wrong too (it flips 18). The count was a
    measurement; the attribution was not, and attribution is what this corpus
    exists to hand the AT-416 gate.

      * **AT-416 — FIXED (at408-416-scroll-reach), no longer named here.** Was
        a `hidden` box OUTSIDE an `auto` one: a scrollable pane inside a
        clipping ancestor. `reachOf`/`isReachable` (now `visual_order_reach.js`)
        test the innermost scroller's own box against clips found ABOVE it,
        instead of the glyph's current (scroll-dependent) rect — option B of
        `qa/gates/at416-clip-vs-reach-direction.md`. **UNVERIFIED against this
        corpus with real Chromium**: the RAM gate never cleared in this build
        session (readings 1.47/0.77/0.62/0.90/0.81/0.88 GB over 30 min, other
        concurrent builders holding memory) — see
        `qa/manifests/at408-416-scroll-reach.md`. The prediction is backed by a
        unit harness that `eval()`s the shipped `visual_order_reach.js`
        verbatim against the checker's own recorded probe geometries (P1, P2,
        P6, P7, and the non-overflowing NESTCLIP case), not by the corpus
        itself. If the prediction is wrong in EITHER direction the mechanism
        below still catches it — a shape wrongly left unmarked now fails
        outright instead of passing.
      * **AT-417** — `clip-path` on a box that also scrolls. `_html` puts the
        clip on the OUTERMOST box, so it applies only when that box is `auto`;
        a clip-path on a `hidden` box scrolls nothing and is not AT-417.

    This is not a prediction trusted on faith. Every derived defect becomes an
    `xfail(strict=True)`, so the rule is checked on every run in both directions:
    a shape it wrongly marks red XPASSes and fails, and a shape it wrongly marks
    green fails outright. Measured when AT-416 was still open: exactly the 32
    failing shapes, AT-416 on 20, AT-417 on 14, both on 2 — matching a checker's
    independent count taken by fixing each defect in turn. Post-fix expectation
    (unverified, see above): 14 red shapes, all AT-417.
    """
    defects = []
    if clip_path and shape[0] == "auto":
        defects.append("AT-417")
    return defects


@pytest.fixture(scope="module")
def corpus_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site = tmp_path_factory.mktemp("scroll-invariance-corpus")
    for label, shape, clip_path, tall in CORPUS:
        (site / f"{label}.html").write_text(
            _html(shape, clip_path=clip_path, tall_page=tall), encoding="utf-8")
    return site


@pytest.fixture(scope="module")
def shape_page(corpus_site: Path, serve_dir: Callable[[Path], str]):
    playwright = pytest.importorskip("playwright.sync_api")
    base = serve_dir(corpus_site)
    runner = playwright.sync_playwright().start()
    try:
        browser = runner.chromium.launch(headless=True)
    except Exception as exc:  # browser binary missing on this machine
        # stop the driver: a started-but-never-stopped one leaves a running asyncio
        # loop on this thread and breaks every later TestClient/asyncio.run test.
        runner.stop()
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    page = browser.new_page()

    def visit(label: str):
        page.goto(f"{base}/{label}.html")
        page.wait_for_load_state("domcontentloaded")
        return page

    yield visit
    browser.close()
    runner.stop()


_RESET = """() => {
  document.querySelectorAll('[id^=L]').forEach(el => { el.scrollTop = 0; el.scrollLeft = 0; });
  window.scrollTo(0, 0);
}"""
"""Resetting every box is safe — putting a container back to 0 is the state the
page loaded in, whether or not a reader could have moved it."""

_MOVED = """() => window.scrollY > 0 ||
  Array.from(document.querySelectorAll('[id^=L]')).some(el => el.scrollTop > 0)"""

_SCROLLERS = """() => Array.from(document.querySelectorAll('[id^=L]'))
  .filter(el => {
    // A READER's scroll, not a script's. `el.scrollTop = n` moves an
    // overflow:hidden box perfectly well in Chromium, and the first version of
    // this driver did exactly that: it scrolled boxes nobody can scroll, the
    // detector correctly reported different text, and 50 of 56 shapes came back
    // red. The corpus was measuring the driver. Computed overflow decides.
    const s = getComputedStyle(el);
    const y = /^(auto|scroll)$/.test(s.overflowY) && el.scrollHeight > el.clientHeight;
    const x = /^(auto|scroll)$/.test(s.overflowX) && el.scrollWidth > el.clientWidth;
    return y || x;
  })
  .map(el => el.id)"""


def _states(page) -> list[tuple[str, Callable[[], None]]]:
    """Every scroll state worth visiting, named so a failure says which one.

    The containers are enumerated AT RUNTIME rather than from the shape spec:
    whether a box actually scrolls is the browser's answer, not the fixture
    author's, and assuming it was the fixture author's is how an existing
    fixture came to hold the AT-416 shape without exhibiting it.
    """
    out: list[tuple[str, Callable[[], None]]] = []
    for scroller in page.evaluate(_SCROLLERS):
        for where, expr in (("mid", "el.scrollHeight / 2"), ("max", "el.scrollHeight")):
            out.append((
                f"{scroller}:{where}",
                lambda s=scroller, e=expr: page.eval_on_selector(
                    f"#{s}", f"el => {{ el.scrollTop = {e}; el.scrollLeft = el.scrollWidth; }}"),
            ))
    out.append(("window:bottom",
                lambda: page.evaluate("window.scrollTo(0, document.body.scrollHeight)")))
    return out


@pytest.mark.parametrize(
    "label",
    [pytest.param(label, marks=pytest.mark.xfail(
        strict=True, reason=" + ".join(_open_defects(shape, clip))))
     if _open_defects(shape, clip) else label
     for label, shape, clip, _tall in CORPUS],
)
def test_what_is_reported_does_not_change_when_anything_is_scrolled(shape_page, label: str) -> None:
    """The floor: a scroll may reorder the result, never change its contents.

    Sorted-character equality is the assertion because scrolling a pane DOES
    legitimately change visual order — two texts can come to share a screen row
    and interleave. What may never change is which glyphs are there at all."""
    page = shape_page(label)
    page.evaluate(_RESET)
    at_rest = sorted(visual_text(page))
    # The positive control, on every generated page: without it a detector that
    # returned nothing would be trivially invariant and pass this whole corpus.
    assert "CONTROL_QUARTERLY_REPORT" in visual_text(page)

    moved = False
    for name, scroll in _states(page):
        page.evaluate(_RESET)
        scroll()
        moved = moved or page.evaluate(_MOVED)
        # Force a layout flush before measuring. Without it this corpus was
        # NON-DETERMINISTIC — 33 failures on one run, 32 on the next — because a
        # scroll is committed asynchronously and `visual_text` measures rects.
        # A flaky instrument is worse than no instrument, and C7 forbids shipping
        # one, so the settle is part of the probe rather than a retry loop.
        page.evaluate("() => { document.body.offsetHeight; }")
        page.wait_for_timeout(30)
        assert sorted(visual_text(page)) == at_rest, f"{label} changed after {name}"

    # AT-426: a page on which no scroll state actually MOVED anything tests
    # nothing, and would pass whatever the detector did. Asserted rather than
    # trusted, so a shape added later that cannot scroll fails here instead of
    # joining the passing count.
    assert moved, f"{label}: no scroll state moved the window or any container"
