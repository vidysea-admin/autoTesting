"""T-050: 3 hand-written Pathlynks login cases (best/worst/edge), run headed and
graded for real. Contract: qa/contracts/pathlynks-first-run.md F1-F5.

Umesh approved this live run explicitly (2026-09-03). `headed=True` is an
in-memory override only -- `projects/pathlynks/project.json` stays
`headed=false` (the unattended-run default), per T-030's own note that a
future human-supervised exploration can override per-run.

Grading now uses `LangChainFallbackProvider` (T-050b) -- Anthropic first,
falling through to Gemini (the only one with a working key today), so this
never depends on one vendor. `--no-grade` runs the browser part only, kept
for the day every configured tier is genuinely unavailable.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.ids import ulid
from autotester.core.paths import ProjectPaths
from autotester.providers.base import Provider
from autotester.providers.langchain_fallback import LangChainFallbackProvider
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, EvidenceKind
from autotester.schema.flowspec import Step
from autotester.schema.verdict import Criterion, Rubric
from autotester.stages.execute import run_case
from autotester.stages.grade import grade
from autotester.stages.run_record import now_utc, record_run, run_id_lines
from autotester.store import ProjectStore

SIGNIN_EMAIL = 'input[name="identifier"]'
SIGNIN_PASSWORD = 'input[name="password"]'
SIGNIN_SUBMIT = 'button[type="submit"]:has-text("Login")'
WRONG_PASSWORD = "Wr0ng-Password-Deliberately-Not-Real!"  # not a secret; never a real credential
POST_SUBMIT_MAX_WAIT_MS = 8000  # bounded ceiling for the poll below, not a blind sleep
POST_SUBMIT_POLL_MS = 250


def build_cases(project_slug: str, base_url: str) -> list[Case]:
    """`base_url` is a literal, not a secret -- it goes straight into each case's
    NAVIGATE step so a persisted case is standalone re-runnable via execute.py,
    with no template marker only this script would know how to resolve."""
    return [
        Case(
            project=project_slug, flow_id="flow_login", kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title="Login with correct credentials",
            rationale="proves the credential boundary + execute/grade pipeline against a real "
                      "product end to end",
            steps=[
                Step(order=1, action=Action.NAVIGATE, target=base_url),
                Step(order=2, action=Action.FILL, target=SIGNIN_EMAIL,
                     value="{{SECRET:PATHLYNKS_USER_EMAIL}}"),
                Step(order=3, action=Action.FILL, target=SIGNIN_PASSWORD,
                     value="{{SECRET:PATHLYNKS_USER_PASSWORD}}"),
                Step(order=4, action=Action.CLICK, target=SIGNIN_SUBMIT),
            ],
        ),
        Case(
            project=project_slug, flow_id="flow_login", kind=CaseKind.WORST,
            case_class=CaseClass.AUTH_WRONG_CREDS, title="Login with correct email, wrong password",
            rationale="a real account with a deliberately wrong password must be rejected",
            steps=[
                Step(order=1, action=Action.NAVIGATE, target=base_url),
                Step(order=2, action=Action.FILL, target=SIGNIN_EMAIL,
                     value="{{SECRET:PATHLYNKS_USER_EMAIL}}"),
                Step(order=3, action=Action.FILL, target=SIGNIN_PASSWORD, value=WRONG_PASSWORD),
                Step(order=4, action=Action.CLICK, target=SIGNIN_SUBMIT),
            ],
        ),
        Case(
            project=project_slug, flow_id="flow_login", kind=CaseKind.EDGE,
            case_class=CaseClass.INPUT_EMPTY, title="Submit the login form empty",
            rationale="client-side/server-side validation must stop an empty submit",
            steps=[
                Step(order=1, action=Action.NAVIGATE, target=base_url),
                Step(order=2, action=Action.CLICK, target=SIGNIN_SUBMIT),
            ],
        ),
    ]


def make_rubric(case: Case) -> Rubric:
    return Rubric(
        id=f"rub_{case.id}",
        case_id=case.id,
        criteria=[
            Criterion(id="landed", text=(
                "For the BEST case: the final URL evidence shows the browser left the sign-in "
                "page and landed somewhere else (a dashboard). For WORST/EDGE cases: the final "
                "URL evidence shows the browser is STILL on the sign-in page (login was "
                "rejected or never attempted)."
            )),
        ],
        no_fire=["exact wording of any error message shown by the product"],
    )


def _wait_for_redirect_or_timeout(session: BrowserSession, signin_url: str) -> None:
    """Poll until the URL leaves `signin_url` or the ceiling elapses -- never raises.

    A FIXED sleep here raced the real redirect timing: found running this for real
    (checker cycle 1) that a fixed 4s wait sometimes fired before Pathlynks' own
    async "Logging in..." spinner finished, so BEST's post-submit screenshot/URL
    still showed the sign-in page and the case flipped a FALSE FAIL on a login
    that actually succeeded a moment later. WORST/EDGE are SUPPOSED to still be on
    `signin_url` when this returns (login was rejected/never attempted) -- this
    function is silent either way, it only stops guessing too early.
    """
    elapsed = 0
    while elapsed < POST_SUBMIT_MAX_WAIT_MS:
        if session.page.url != signin_url:
            return
        session.page.wait_for_timeout(POST_SUBMIT_POLL_MS)
        elapsed += POST_SUBMIT_POLL_MS


def run_one_case(case: Case, session: BrowserSession, judge: Provider | None, run_id: str,
                 mask_limit: float | None = None):
    """`mask_limit` is the project's own `image_mask_limit` (AT-1384): without it the dashboard
    screenshot is judged at the stricter default, withheld, and the case reads INCONCLUSIVE."""
    # execute.py::run_case snapshots ALL of session.state.evidence, which is cumulative for the
    # whole (reused) session, not scoped per case -- slice to just what THIS case adds, else
    # case 2's RawResult would also carry case 1's evidence (found running this for real).
    signin_url = case.steps[0].target  # every case's own step 1 is NAVIGATE to the sign-in page
    start = len(session.state.evidence)
    result = run_case(case, session)
    _wait_for_redirect_or_timeout(session, signin_url)
    session.screenshot(f"{case.kind.value}-final")
    landed_url = session.secrets.redactor().scrub(session.page.url)
    session._record(EvidenceKind.URL, landed_url, label="post-submit URL")
    result.evidence = list(session.state.evidence[start:])

    verdict = (grade(make_rubric(case), result, run_id, judge, mask_limit=mask_limit)
               if judge is not None else None)
    return result, verdict


def main() -> None:
    grade_enabled = "--no-grade" not in sys.argv
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")

    store = ProjectStore("pathlynks")
    project = store.load_project()
    if project is None:
        raise RuntimeError("projects/pathlynks/project.json not found")
    headed_project = project.model_copy(update={"headed": True})

    paths = ProjectPaths("pathlynks")
    secrets = SecretStore.load(headed_project, paths.env_file)

    run_id = f"run-{ulid()}"
    run_dir = paths.run_dir(run_id)
    cases = build_cases(project.slug, project.base_url)
    for case in cases:
        store.add_case(case)

    judge: Provider | None = None
    if grade_enabled:
        judge = LangChainFallbackProvider()
        if not judge.available():
            raise RuntimeError("no provider in the fallback chain is configured (no "
                                "ANTHROPIC_API_KEY/GEMINI_API_KEY/OLLAMA_BASE_URL/"
                                "OPENAI_API_KEY) -- pass --no-grade to run browser-only")
    else:
        print("grading skipped (--no-grade) -- running the browser part only")

    # This script tests the LOGIN FLOW itself, so it needs a genuinely logged-out browser both
    # ACROSS runs and WITHIN one run. Two distinct problems, two fixes, both still needed:
    #  1. Cross-run: the shared profiles/pathlynks/ profile (used by onboarding/manual-login for
    #     deliberate session reuse) persists cookies forever, so a prior successful BEST case
    #     left THIS script's next run pre-authenticated (found running this for real: all 3
    #     cases errored waiting for a login field the page had already navigated away from).
    #     Fixed with a dedicated profile, wiped clean before every run.
    #  2. Within-run: even on a fresh profile, once BEST logs in successfully, the SAME session
    #     stays authenticated for whichever case runs next -- confirmed by re-running after fix
    #     #1 alone: BEST correctly went PASS, but WORST/EDGE (which ran after it, in file order)
    #     still errored the exact same way. BEST must still run last within one process.
    login_test_paths = ProjectPaths("pathlynks-login-test")
    shutil.rmtree(login_test_paths.profile_dir, ignore_errors=True)
    run_order = sorted(cases, key=lambda c: 0 if c.kind is not CaseKind.BEST else 1)

    started_at = now_utc()
    session = BrowserSession(headed_project, secrets, run_dir, login_test_paths)
    session.start()
    results = []
    try:
        for case in run_order:
            result, verdict = run_one_case(case, session, judge, run_id,
                                           mask_limit=headed_project.image_mask_limit)
            store.save_result(run_id, result)
            if verdict is not None:
                store.save_verdict(run_id, verdict)
            results.append((case, result, verdict))
            session.goto(project.base_url)  # reset to sign-in page between cases
    finally:
        session.close()

    record_run(store, run_id, project.slug, [c.id for c, _, _ in results], started_at, now_utc())

    for case, result, verdict in results:
        verdict_str = (
            f"{verdict.result.value} ({verdict.grader_provider})" if verdict else "(deferred)"
        )
        print(f"{case.kind.value:5s} {case.id}  outcome={result.outcome.value:9s} "
              f"verdict={verdict_str}")
    for line in run_id_lines(run_id, run_dir):
        print(line)


if __name__ == "__main__":
    main()
