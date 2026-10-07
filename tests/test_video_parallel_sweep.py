"""ISS-t191-run-video-1 (critical, T-191 fix cycle 2), real browser: two
sessions sharing one `run_dir` -- exactly what `stages/parallel_run.py::
default_session_factory` gives every parallel-run sibling (AT-572) -- must
never let one session's teardown delete another's already-finished,
not-yet-renamed video.

`VideoMixin.end_case_video()` finalizes a case in three separate, non-atomic
steps: `page.close()` (flushes the recording to a temp file inside
`_video_scratch`) -> read `video.path()` -> `temp_path.replace(final_path)`
(the rename to safety). Between the first and third step the file is a
completed, ordinary, unlocked file sitting in the scratch directory. Before
this fix, `BrowserSession.close()`'s `_sweep_orphan_videos()` ran an
unconditional `shutil.rmtree` on the whole (shared) `_video_scratch`
directory the instant *any* session using that `run_dir` closed -- destroying
a slower sibling's finished-but-not-yet-renamed video with no error raised
anywhere (`end_case_video` treats a missing temp file as an ordinary "no
video").

Reproduced with two REAL `BrowserSession`s, each driven from its own
`threading.Thread` -- mirroring `stages/parallel_run.py::run_cases`'s actual
`ThreadPoolExecutor` model, and required by Playwright's sync API (two
`sync_playwright().start()` calls in one thread raise "already inside an
asyncio loop"). The two threads are ordered with `threading.Event`s, not
`sleep`, so the interleaving is exact and deterministic rather than
timing-dependent -- this test must not itself be flaky under load.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from timing_scale import timing_scale

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import ProjectPaths
from autotester.schema.project import Project

SITE = Path(__file__).resolve().parent / "fixtures" / "login_site"
_WAIT_S = 30.0 * timing_scale()


def _skip_if_no_chromium() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    try:
        with sync_api.sync_playwright() as pw:
            pw.chromium.launch(headless=True).close()
    except Exception as exc:  # pragma: no cover - browser binary missing
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")


def _project(base_url: str) -> Project:
    return Project(slug="video-parallel-demo", name="Video Parallel Demo", base_url=base_url,
                   allowed_domains=["127.0.0.1"], headed=False)


def test_two_sessions_sharing_a_run_dir_do_not_lose_each_others_video(
    tmp_path: Path, serve_dir: Callable[[Path], str],
) -> None:
    """Mirrors `default_session_factory`: two real `BrowserSession`s, same
    `run_dir`, different profile dirs (own `ProjectPaths`) -- exactly how
    parallel siblings are constructed. Thread B finishes recording first (its
    page is closed, so Playwright has flushed the `.webm` to disk) but is
    held, by an `Event`, in the window before its rename to safety. Thread A
    finishes its own case cleanly, then closes its session -- the moment the
    unfixed sweep can destroy B's file. B is then released to attempt its
    rename and the test asserts its file survived."""
    _skip_if_no_chromium()
    base = serve_dir(SITE)
    project = _project(f"{base}/login.html")
    secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    run_dir = tmp_path / "shared_run"

    b_unrenamed = threading.Event()  # B: recording flushed to disk, rename not yet done
    a_closed = threading.Event()     # A: end_case_video() + close() (the sweep) both ran
    errors: list[BaseException] = []
    results: dict[str, object] = {}

    def _run_a() -> None:
        session = BrowserSession(project, secrets, run_dir,
                                 ProjectPaths("video-parallel-demo-a", tmp_path),
                                 record_video=True)
        try:
            session.start()
            session.begin_case_video("case_a")
            session.page.goto(f"{base}/login.html")
            rel = session.end_case_video()
            if rel != "case_a.webm":
                raise AssertionError(f"A's own video path unexpected: {rel!r}")
            if not b_unrenamed.wait(timeout=_WAIT_S):
                raise AssertionError("B never reached the unrenamed window")
            session.close()  # the sweep this unit is fixing
        except BaseException as exc:  # surfaced on the main thread below
            errors.append(exc)
        finally:
            a_closed.set()

    def _run_b() -> None:
        session = BrowserSession(project, secrets, run_dir,
                                 ProjectPaths("video-parallel-demo-b", tmp_path),
                                 record_video=True)
        try:
            session.start()
            session.begin_case_video("case_b")
            session.page.goto(f"{base}/login.html")
            # Replicate end_case_video()'s first step by hand, stopping
            # BEFORE the rename -- the exact non-atomic window a faster
            # sibling's close() can land in.
            page, case_id = session._page, session._video_case_id
            video = page.video
            session._page = None
            page.close()
            temp_path = Path(video.path())
            if not temp_path.exists():
                raise AssertionError("B's finished recording did not exist before signalling A")
            results["temp_path"] = temp_path
            results["case_id"] = case_id
            b_unrenamed.set()
            if not a_closed.wait(timeout=_WAIT_S):
                raise AssertionError("A never finished closing")
            final_path = run_dir / f"{case_id}.webm"
            if temp_path.exists():
                temp_path.replace(final_path)
            results["final_path"] = final_path
        except BaseException as exc:  # surfaced on the main thread below
            errors.append(exc)
        finally:
            session.close()

    t_a = threading.Thread(target=_run_a, name="session-a")
    t_b = threading.Thread(target=_run_b, name="session-b")
    t_b.start()
    t_a.start()
    t_a.join(timeout=_WAIT_S + 5)
    t_b.join(timeout=_WAIT_S + 5)

    assert not errors, f"thread(s) raised: {errors!r}"
    final_path = results.get("final_path")
    assert isinstance(final_path, Path), "B never reached its own finalize step"
    assert final_path.exists(), (
        "B's already-finished video must survive A's teardown of a SHARED "
        "run_dir -- ISS-t191-run-video-1"
    )
    assert final_path.stat().st_size > 0
