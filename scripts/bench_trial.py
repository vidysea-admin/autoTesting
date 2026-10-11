"""T-120: the north star made measurable — first real human-vs-AI trial scorecard.

Contract: qa/contracts/bench.md K1-K5. Reuses the T-110 fixture regression
(tests/fixtures/regression_site/, login.broken.html) as a real seeded corpus,
runs the real AutoTester pipeline against it, and computes the scorecard
through BenchTrial.score. The "human" side is a documented oracle baseline,
not a live timed trial -- no tester was available this cycle (see the
contract's Purpose section for why this is the honest choice, not a shortcut).
"""

from __future__ import annotations

import functools
import http.server
import shutil
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.bench import BenchCorpus
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind, Severity
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import Run
from autotester.schema.verdict import Criterion, Rubric
from autotester.stages import bench
from autotester.stages.execute import run_case
from autotester.stages.grade import grade
from autotester.store.project_store import ProjectStore

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regression_proof import seat_demo_cases

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "regression_site"
LOGIN_GOOD = FIXTURE_DIR / "login.html"
LOGIN_BROKEN = FIXTURE_DIR / "login.broken.html"


class _NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_server() -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(_NoCacheHandler, directory=str(FIXTURE_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def build_cases(project_slug: str, base_url: str) -> list[Case]:
    return [
        Case(
            project=project_slug, flow_id="flow_login", kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title="Login with correct credentials",
            rationale="the seeded bug this corpus exists to detect",
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
            rationale="an unrelated case -- a FAIL here would be a false positive",
            steps=[Step(order=1, action=Action.NAVIGATE, target=f"{base_url}/index.html")],
        ),
    ]


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
    cases = seat_demo_cases(store, build_cases(project.slug, base_url))  # AT-434
    login_case, _home_case = cases
    judge = LangChainFallbackProvider()

    good_backup = LOGIN_GOOD.read_text(encoding="utf-8")
    shutil.copy(LOGIN_BROKEN, LOGIN_GOOD)  # seed the bug for the whole trial

    verdicts = []
    t0 = time.monotonic()
    try:
        paths = ProjectPaths(project.slug)
        secrets = SecretStore.load(project, paths.env_file)
        run_id = f"run-bench-{ulid()}"
        session = BrowserSession(project, secrets, paths.run_dir(run_id), paths)
        session.start()
        try:
            for case, selector in zip(cases, ["#result", "#heading"], strict=True):
                result, verdict, text = run_and_grade(case, session, judge, run_id, selector)
                store.save_result(run_id, result)
                store.save_verdict(run_id, verdict)
                verdicts.append(verdict)
                print(f"{case.title}: {verdict.result.value}  (observed: {text!r})")
        finally:
            session.close()
        store.save_run(Run(id=run_id, project=project.slug, case_ids=[c.id for c in cases]))
    finally:
        LOGIN_GOOD.write_text(good_backup, encoding="utf-8")
        server.shutdown()
    duration_s = time.monotonic() - t0

    corpus = BenchCorpus(
        id="corpus_regression_demo_login", mode="fixture",
        app="regression-demo", build_ref="login.broken.html",
        seeded_bugs=[
            bench.seeded_bug(
                bug_id="bug_login_password",
                description="Login rejects the correct password (pass123 -> pass124 typo)",
                location="/login.html", severity=Severity.S1,
                detect_hint="Login with correct credentials should succeed but shows an error",
            )
        ],
        material_refs=["tests/fixtures/regression_site/"],
    )
    store.save_bench_corpus(corpus)

    case_bug_map = {login_case.id: "bug_login_password"}  # home_case NOT mapped -> FAIL there = FP
    ai_trial = bench.run_autotester_trial(
        f"trial_ai_{ulid()}", corpus, verdicts, case_bug_map, duration_s,
        ordering="independent_parallel",
    )
    # AT-543: the human side has never been timed by a real tester — passing a
    # hardcoded 300.0 turned the scorecard's "wins on time" row into a
    # comparison against a made-up constant. None preserves unavailable timing.
    human_trial = bench.oracle_human_trial(f"trial_human_{ulid()}", corpus)
    store.save_bench_trial(ai_trial)
    store.save_bench_trial(human_trial)

    card = bench.scorecard(corpus, [ai_trial, human_trial])
    print("\n--- SCORECARD (via BenchTrial.score) ---")
    for label, score in card.items():
        print(f"{label}: {score}")

    ok = card["autotester-real-run"]["detected"] == card["autotester-real-run"]["seeded"] == 1
    verdict = "PASS" if ok else "FAIL"
    print(f"\nBENCH TRIAL: {verdict} — AutoTester detected the seeded bug for real.")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
