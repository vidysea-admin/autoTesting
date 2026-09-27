"""T-110: break a feature, confirm exactly that case FAILs while an unrelated
case stays PASS. Contract: qa/contracts/regression-proof.md P1-P5.

Umesh approved this project touching only local, self-served fixture pages
(tests/fixtures/regression_site/) -- never Pathlynks or any other real
product, and it never mutates the fixture's canonical "good" state (the
broken variant is swapped in for one run, then restored). This is the
"the actual product promise: new work cannot silently break old work" made
literal and provable, without needing write access to a real staging
environment this system doesn't control.
"""

from __future__ import annotations

import functools
import http.server
import shutil
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Run
from autotester.schema.verdict import Criterion, Rubric
from autotester.stages.execute import run_case
from autotester.stages.grade import grade
from autotester.store.project_store import ProjectStore

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "regression_site"
LOGIN_GOOD = FIXTURE_DIR / "login.html"
LOGIN_BROKEN = FIXTURE_DIR / "login.broken.html"


@contextmanager
def _swapped_fixture(good_path: Path, broken_path: Path) -> Iterator[None]:
    """Copy `broken_path` over `good_path` for the body's duration, then restore
    `good_path`'s original content -- even if the body raises or is interrupted
    (AT-560: `good_path` is a TRACKED fixture; an interrupted run must never
    leave it in the broken state)."""
    backup = good_path.read_text(encoding="utf-8")
    try:
        shutil.copy(broken_path, good_path)
        yield
    finally:
        good_path.write_text(backup, encoding="utf-8")


class _NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """The BEFORE/AFTER runs reuse one persistent browser profile (same as a
    real project's login-persistence design) -- Chromium's own HTTP cache
    would otherwise keep serving the pre-regression login.html on the AFTER
    run, since a plain http.server sends no cache-control headers at all
    (found running this for real: the AFTER run showed the OLD, working page).
    """

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_server() -> tuple[http.server.ThreadingHTTPServer, int]:
    # functools.partial, not a `directory=...` class attribute -- SimpleHTTPRequestHandler's
    # own __init__ unconditionally overwrites self.directory from its `directory` kwarg
    # (defaulting to os.getcwd() when omitted), so a class-level override is silently ignored
    # and every request 404s against the wrong root (found running this for real).
    handler = functools.partial(_NoCacheHandler, directory=str(FIXTURE_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def build_cases(project_slug: str, base_url: str) -> list[Case]:
    return [
        Case(
            project=project_slug, flow_id="flow_login", kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title="Login with correct credentials",
            rationale="the case T-110 deliberately breaks",
            steps=[
                Step(order=1, action=Action.NAVIGATE, target=f"{base_url}/login.html"),
                Step(order=2, action=Action.FILL, target="#email", value="test@example.com"),
                Step(order=3, action=Action.FILL, target="#password", value="pass123"),
                Step(order=4, action=Action.CLICK, target="#submit"),
            ],
        ),
        Case(
            project=project_slug, flow_id="flow_home", kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title="Homepage loads",
            rationale="an unrelated case that must stay PASS after the login regression",
            steps=[Step(order=1, action=Action.NAVIGATE, target=f"{base_url}/index.html")],
        ),
    ]


def seat_demo_cases(store: ProjectStore, cases: list[Case]) -> list[Case]:
    """Put `cases` on file as the ONLY copy of each journey, and return them (AT-434).

    A case id covers its steps, and every step target here carries the fixture
    server's random port, so `add_case`'s idempotency never fired: each run added
    two new cases, and the demo reached 44 (22 copies of each journey, each on a
    port that no longer exists). A stale copy — same project, flow and title,
    different id — is removed first. Its old runs and verdicts are history and
    stay, exactly as `delete_case` promises; any other case is left alone."""
    journeys = {(c.project, c.flow_id, c.title) for c in cases}
    keep = {c.id for c in cases}
    for existing in store.list_cases():
        if (existing.project, existing.flow_id, existing.title) in journeys \
                and existing.id not in keep:
            store.delete_case(existing.id)
    for case in cases:
        store.add_case(case)
    return cases


def make_rubric(case: Case, expect_text: str) -> Rubric:
    return Rubric(
        id=f"rub_{case.id}", case_id=case.id,
        criteria=[Criterion(id="c1", text=(
            f"The DOM evidence shows the page's own text reading exactly '{expect_text}' "
            "(look for an evidence entry whose path contains this text). If you cite this as a "
            "failure, use criterion id 'c1' exactly as given here -- do not invent a different id."
        ))],
        no_fire=["visual styling"],
    )


def run_and_grade(case: Case, session: BrowserSession, judge, run_id: str, selector: str):
    start = len(session.state.evidence)
    result = run_case(case, session)
    text = session.page.locator(selector).text_content() or "(empty)"
    session._record(EvidenceKind.DOM, f"{selector} text: {text!r}")
    result.evidence = list(session.state.evidence[start:])
    expect = "Login successful" if selector == "#result" else "Welcome to the demo site"
    verdict = grade(make_rubric(case, expect), result, run_id, judge)
    return result, verdict, text


def run_suite(project: Project, cases: list[Case], store: ProjectStore, judge, label: str):
    paths = ProjectPaths(project.slug)
    secrets = SecretStore.load(project, paths.env_file)
    run_id = f"run-{label}-{ulid()}"
    session = BrowserSession(project, secrets, paths.run_dir(run_id), paths)
    session.start()
    outcomes = {}
    try:
        for case, selector in zip(cases, ["#result", "#heading"], strict=True):
            result, verdict, text = run_and_grade(case, session, judge, run_id, selector)
            store.save_result(run_id, result)
            store.save_verdict(run_id, verdict)
            outcomes[case.title] = (verdict.result.value, text)
    finally:
        session.close()
    store.save_run(Run(id=run_id, project=project.slug, case_ids=[c.id for c in cases]))
    return outcomes


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    server, port = start_server()
    base_url = f"http://127.0.0.1:{port}"

    project = Project(
        slug="regression-demo", name="Regression Proof Demo", base_url=f"{base_url}/index.html",
        allowed_domains=["127.0.0.1"], headed=True,
    )
    store = ProjectStore("regression-demo")
    store.save_project(project)
    cases = seat_demo_cases(store, build_cases(project.slug, base_url))
    judge = LangChainFallbackProvider()

    try:
        print("--- BEFORE (working build) ---")
        before = run_suite(project, cases, store, judge, "before")
        for title, (result, text) in before.items():
            print(f"{title}: {result}  (observed: {text!r})")

        print("\n--- injecting the regression (login.html -> login.broken.html) ---")
        with _swapped_fixture(LOGIN_GOOD, LOGIN_BROKEN):
            print("--- AFTER (broken build) ---")
            after = run_suite(project, cases, store, judge, "after")
            for title, (result, text) in after.items():
                print(f"{title}: {result}  (observed: {text!r})")
    finally:
        server.shutdown()

    login_title, home_title = cases[0].title, cases[1].title
    ok = (
        before[login_title][0] == "PASS"
        and before[home_title][0] == "PASS"
        and after[login_title][0] == "FAIL"
        and after[home_title][0] == "PASS"
    )
    print(f"\nREGRESSION PROOF: {'PASS' if ok else 'FAIL'} — exactly the login case flipped, "
          f"the homepage case did not.")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
