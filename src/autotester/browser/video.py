"""Per-case video recording for `BrowserSession` (T-191/AT-587).

Split out the same way `evidence.py` was (AT-567): a distinct concern from
the lifecycle/action methods in `session.py`. `BrowserSession` mixes this in
alongside `EvidenceMixin` so `begin_case_video`/`end_case_video` behave as
ordinary methods on `self` (`self._context`, `self._page`, `self.state`).

Mechanism (contract run-video.md plan-decisions 1, 3, 5): Playwright records
video PER PAGE, not per context -- every page a context creates while
`record_video_dir` is set gets its own file, finalized when that page closes.
A session's context is shared across every case in the serial route (login
continuity), so "one video per case" means swapping to a FRESH page at the
start of each case and closing it at the end, never reusing one page across
cases the way screenshots reuse the session's page. The masking CSS must
survive every navigation the case's steps make, not just the page it started
on -- `page.add_style_tag()` (what `screenshot()` uses) injects into the
CURRENT document only, and a plain `page.goto()` replaces that document
wholesale, silently dropping it (measured empirically while building this
unit: a style tag added before `goto()` read back as `display: none`'s
absence -- `webkitTextSecurity: 'none'` -- the instant the first NAVIGATE
step ran). `page.add_init_script()` re-runs its script on every new document
this page ever loads, which is what actually gives V3 its "from the moment
the page is created, for every frame" guarantee; it evaluates at
`document_start`, before `document.documentElement` necessarily exists yet
(also measured directly: a bare `document.head || document.documentElement`
append raised `Cannot read properties of null` on a fresh navigation), so
`_MASK_INIT_SCRIPT` retries via a `MutationObserver` until a root exists.
"""

from __future__ import annotations

from pathlib import Path

from autotester.browser.evidence import MASK_CSS

_MASK_INIT_SCRIPT = f"""(() => {{
  function install() {{
    const root = document.head || document.documentElement;
    if (!root) return false;
    const s = document.createElement('style');
    s.textContent = {MASK_CSS!r};
    root.appendChild(s);
    return true;
  }}
  if (!install()) {{
    const mo = new MutationObserver(() => {{ if (install()) mo.disconnect(); }});
    mo.observe(document, {{childList: true, subtree: true}});
  }}
}})();"""
"""Re-injects `MASK_CSS` as a `<style>` element on EVERY document this page
loads (`add_init_script`, not `add_style_tag` -- see the module docstring for
why the obvious approach silently fails). The `MutationObserver` fallback
covers `document_start`, when neither `document.head` nor
`document.documentElement` is guaranteed to exist yet."""

VIDEO_DIR_NAME = "_video_scratch"
"""Playwright's own random-named output directory for this session's video
files -- never the final evidence path. `end_case_video` renames out of here
into the deterministic, run-relative path evidence uses everywhere else.
`BrowserSession` nests this under a per-session subdirectory
(`run_dir/_video_scratch/<session-id>`) rather than using it bare: parallel
siblings share one `run_dir` (`parallel_run.py::default_session_factory`,
AT-572), and before that nesting existed, `close()`'s unconditional
`shutil.rmtree` of this bare directory could delete a still-recording
sibling's already-finished, not-yet-renamed video the instant any other
sibling finished first (ISS-t191-run-video-1, T-191 cycle 2). Nesting per
session means each session only ever sweeps its own subdirectory."""

MAX_VIDEO_DURATION_S = 1200.0
"""20 minutes -- the gate's own "15-20 minute walkthrough" language (T-191
contract V6). A case that runs longer than this has its video dropped
regardless of verdict, as a disk safety net: `record_video_size` bounds
bytes-per-second, this bounds seconds. Enforced in
`stages/run_case_pipeline.py::_finalize_video`, not here -- this module only
records; the pipeline decides what survives (single choke point, V7)."""

VIDEO_OVERHEAD_MB = 128.0
"""Conservative resident-memory estimate for one Chromium page's video
encoder buffer at `RECORD_VIDEO_SIZE`, on top of
`parallel_run.DEFAULT_PER_CONTEXT_MB` -- read by `plan_parallel_run`'s
`video_enabled` argument (V6)."""


class VideoMixin:
    """`begin_case_video()` / `end_case_video()` -- mixed into `BrowserSession`."""

    def begin_case_video(self, case_id: str) -> None:
        """Swap to a fresh page for `case_id`. A no-op when this session was
        not started with `record_video=True` (`self.record_video` is False):
        every other session keeps behaving exactly as before this unit. Also
        a no-op when `self._context` is `None` -- a session whose `start()`
        was replaced by a test double (many existing tests fake `start()` to
        skip the real browser launch) never created a context to record
        from, so there is nothing to swap a page on; this mirrors
        `record_video=False` rather than raising on those pre-existing
        fixtures."""
        if not getattr(self, "record_video", False) or self._context is None:
            return
        self._timeout()
        old_page = self._page
        self._page = self._context.new_page()
        self._timeout()
        self._page.add_init_script(_MASK_INIT_SCRIPT)
        self._timeout()
        self._video_case_id = case_id
        if old_page is not None:
            with _ignore_close_errors():
                old_page.close()

    def end_case_video(self) -> str | None:
        """Close the case's page (finalizing its recording) and return the
        run-relative path evidence uses, or `None` when video is off for this
        session. Renames Playwright's randomly-named output file to
        `<evidence_prefix>/<case_id>.webm` (or `<case_id>.webm` with no
        prefix) -- the same nesting convention `EvidenceMixin.screenshot`
        already uses for parallel siblings sharing one `run_dir`."""
        if not getattr(self, "record_video", False):
            return None
        page, case_id = self._page, getattr(self, "_video_case_id", None)
        if page is None or case_id is None:
            return None
        video = page.video
        self._page = None
        with _ignore_close_errors():
            page.close()
        if video is None:
            return None
        try:
            temp_path = Path(video.path())
        except Exception:
            return None
        prefix = getattr(self.state, "evidence_prefix", "") or ""
        rel = f"{prefix}/{case_id}.webm" if prefix else f"{case_id}.webm"
        final_path = self.state.run_dir / rel
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if temp_path.exists():
            temp_path.replace(final_path)
        return rel if final_path.exists() else None


class _ignore_close_errors:
    """A page that already errored mid-case may fail to close cleanly
    (crashed renderer, already-closed target) -- never let cleanup itself
    raise and mask the case's real outcome."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_exc: object) -> bool:
        return True
