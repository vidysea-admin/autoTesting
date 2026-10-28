"""An unmet assertion also records what the page SHOWED (inbox 2026-10-28 line 12).

Before this, a failed `visible_text` assertion recorded only `assert visible_text: unmet
(expected to contain 'Dashboard')`. The reason the user sees on a real login failure (an
"Invalid credentials" alert) lived only in a screenshot, and with image withholding
(`mask_exceeds_limit`) the case became INCONCLUSIVE with no readable reason. The fix records a
bounded excerpt of visible alert/error text as one extra DOM evidence row (never an `assert `
row, so the unmet counters in `stages/grade*.py` are untouched).

Two layers: the JS extractor against a real Chromium page (skipped when no browser binary), and
the Python wiring against the fake page used by `test_execute.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_execute import LOGIN, make_case, make_project, session_with_fake_page

from autotester.browser import assertions, error_text
from autotester.browser.secrets import SecretStore
from autotester.schema.enums import Action, EvidenceKind, Outcome
from autotester.schema.flowspec import ExpectedState, Step
from autotester.stages.execute import run_case

LABEL = "error text on page"


def _rows(evidence: list) -> list:
    return [e for e in evidence if e.kind is EvidenceKind.DOM and e.path.startswith(LABEL)]


def _expect_dashboard(session) -> list:
    return assertions.assert_expected(
        session, ExpectedState(visible_text=["Dashboard"]), timeout_ms=0, step_order=2)


# -- wiring (fake page) -----------------------------------------------------------

def test_unmet_assertion_records_the_visible_alert_text_as_dom_evidence(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Sign in"
    session.page.evaluate = lambda js: ["Invalid credentials"]

    evidence = _expect_dashboard(session)

    rows = _rows(evidence)
    assert len(rows) == 1
    assert "Invalid credentials" in rows[0].path
    assert rows[0].step_order == 2
    assert not rows[0].path.startswith("assert ")  # grade.py counts `assert ... unmet` rows only
    assert rows[0] in session.state.evidence


def test_met_assertion_records_no_error_text_and_never_reads_the_page(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Dashboard"
    session.page.evaluate = lambda js: pytest.fail("a met assertion must not scrape error text")

    evidence = _expect_dashboard(session)

    assert _rows(evidence) == []


def test_error_text_goes_through_the_redactor(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)  # .env holds PATHLYNKS_PASSWORD=hunter2
    session.page.body_text = "Sign in"
    session.page.evaluate = lambda js: ["Wrong password hunter2 for this account"]

    rows = _rows(_expect_dashboard(session))

    assert len(rows) == 1 and "hunter2" not in rows[0].path


def test_scrape_failure_or_empty_result_is_silent(tmp_path: Path) -> None:
    for outcome in (RuntimeError("page closed"), [], None, "not a list", [None, 5, "  "]):
        session = session_with_fake_page(tmp_path)
        session.page.body_text = "Sign in"

        def evaluate(js, outcome=outcome):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        session.page.evaluate = evaluate
        evidence = _expect_dashboard(session)
        assert _rows(evidence) == [], outcome
        assert any("assert visible_text: unmet" in e.path for e in evidence)


def test_excerpt_is_bounded(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Sign in"
    session.page.evaluate = lambda js: [f"error number {i} " + "x" * 5000 for i in range(50)]

    rows = _rows(_expect_dashboard(session))

    assert len(rows) == 1
    assert len(rows[0].path) <= error_text.MAX_TOTAL_CHARS + 200
    assert rows[0].path.count("error number") <= error_text.MAX_ITEMS


def test_duplicate_and_contained_fragments_collapse() -> None:
    texts = error_text.clean([
        "Invalid credentials", "Invalid credentials", "Invalid", "  Try   again\n now ",
        "Invalid credentials. Try again now"])
    assert texts == ["Invalid credentials. Try again now"]


def test_run_case_assertion_failed_carries_the_error_text(tmp_path: Path) -> None:
    steps = [
        Step(order=1, action=Action.NAVIGATE, target=LOGIN),
        Step(order=2, action=Action.CLICK, target="button[type=submit]",
             expected={"visible_text": ["Dashboard"]}),
    ]
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Sign in"
    session.page.evaluate = lambda js: ["Invalid credentials"]

    result = run_case(make_case(steps), session)

    assert result.outcome is Outcome.ASSERTION_FAILED
    assert len(_rows(result.evidence)) == 1
    assert "Invalid credentials" in _rows(result.evidence)[0].path


# -- the extractor against a real page ---------------------------------------------

PAGE = """<!doctype html><meta charset=utf-8><title>login</title>
<form class="login-form has-error">
  <label>Email</label><input id=e name=email value="alice@example.org">
  <input id=p type=password value="s3cretpass">
  <div id=a role=alert>Invalid credentials for alice@example.org</div>
  <div class="field-error">Password s3cretpass is too weak</div>
  <div class="toast-error" style="display:none">HIDDEN TOAST</div>
  <div aria-live="polite">Saved draft</div>
  <p>Welcome to the portal, please sign in.</p>
  <button>Sign in</button>
</form>
<div class="Toastify__toast">Session expired</div>
<div class="error-boundary" style="visibility:hidden">INVISIBLE BOUNDARY</div>
"""


@pytest.fixture(scope="module")
def real_page():
    playwright = pytest.importorskip("playwright.sync_api")
    runner = None
    try:
        runner = playwright.sync_playwright().start()
        browser = runner.chromium.launch(headless=True)
    except Exception as exc:  # no browser binary on this machine
        if runner is not None:
            runner.stop()
        pytest.skip(f"chromium unavailable: {type(exc).__name__}")
    page = browser.new_page()
    yield page
    browser.close()
    runner.stop()


def scrape(page, html: str = PAGE) -> str:
    """Load `html` into the real page and return the cleaned excerpts joined by ' | '."""
    page.set_content(html)
    return " | ".join(error_text.clean(page.evaluate(error_text.SCRAPE_JS)))


def test_extractor_finds_visible_alerts_and_toasts(real_page) -> None:
    joined = scrape(real_page)

    assert "Invalid credentials" in joined
    assert "Session expired" in joined
    assert "Saved draft" in joined  # aria-live region


def test_extractor_skips_hidden_elements_and_form_wrappers(real_page) -> None:
    joined = scrape(real_page)

    assert "HIDDEN TOAST" not in joined and "INVISIBLE BOUNDARY" not in joined
    assert "Welcome to the portal" not in joined  # the has-error <form> wrapper holds inputs
    assert "Sign in" not in joined and "Email" not in joined


def test_extractor_never_echoes_filled_input_values(real_page) -> None:
    joined = scrape(real_page)

    assert "alice@example.org" not in joined
    assert "s3cretpass" not in joined
    assert "Invalid credentials for" in joined and "is too weak" in joined


# -- hardening cycle 1 (checker findings F1-F3, F5) --------------------------------

def test_f1_typed_value_with_consecutive_whitespace_or_newline_is_blanked(real_page) -> None:
    joined = scrape(real_page, """<input value="John  Smith"><textarea>line1
line2xx</textarea>
<div role=alert>No account for John  Smith or line1
line2xx here</div>""")

    assert "No account for" in joined
    assert "John Smith" not in joined and "John  Smith" not in joined
    assert "line1" not in joined and "line2xx" not in joined


def test_f2_typed_value_echoed_in_another_case_is_blanked(real_page) -> None:
    joined = scrape(real_page, """<input value="Alice99">
<div role=alert>User ALICE99 is already taken, alice99 too</div>""")

    assert "is already taken" in joined
    assert "alice99" not in joined.lower()


def test_f3_value_typed_in_an_open_shadow_root_is_blanked(real_page) -> None:
    joined = scrape(real_page, """<div id=h></div>
<script>document.getElementById('h').attachShadow({mode:'open'}).innerHTML =
  '<input value="shadowtyped"><div><textarea>deeptyped</textarea></div>';</script>
<div role=alert>Rejected shadowtyped and deeptyped.</div>""")

    assert "Rejected" in joined
    assert "shadowtyped" not in joined and "deeptyped" not in joined


def test_f3_contenteditable_text_is_never_read_as_message_text(real_page) -> None:
    joined = scrape(real_page, """<div role=alert>Failed <b contenteditable>my private draft</b>
 end</div>
<div class=error-box contenteditable=true>an editor body</div>
<div role=alert contenteditable=plaintext-only>another editor</div>
<div contenteditable=true><p class=error-line>nested editor line</p></div>""")

    assert "Failed" in joined
    for leaked in ("private draft", "editor body", "another editor", "nested editor line"):
        assert leaked not in joined


def test_f3_text_inside_an_iframe_is_not_read(real_page) -> None:
    joined = scrape(real_page, """<div role=alert>Outer message
<iframe>FRAME FALLBACK TEXT</iframe>
<iframe srcdoc="<div role=alert>INSIDE FRAME ALERT</div>"></iframe></div>
<iframe srcdoc="<div role=alert>OTHER FRAME ALERT</div>"></iframe>""")

    assert "Outer message" in joined
    assert "FRAME FALLBACK TEXT" not in joined and "FRAME ALERT" not in joined


# -- F5: scrub before the caps ---------------------------------------------------------

def test_f5_secret_straddling_the_item_cap_is_scrubbed_before_the_cut(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)  # .env holds PATHLYNKS_PASSWORD=hunter2
    session.page.body_text = "Sign in"
    session.page.evaluate = lambda js: ["x" * (error_text.MAX_ITEM_CHARS - 3) + "hunter2 tail"]

    rows = _rows(_expect_dashboard(session))

    assert len(rows) == 1 and "hun" not in rows[0].path


def test_f5_secret_straddling_the_total_cap_is_scrubbed_before_the_cut(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)
    session.page.body_text = "Sign in"
    first = "a" * 198
    second = "b" * 198
    third = "c" * 190 + "hunter2"  # starts inside the 600-char body, ends after it
    session.page.evaluate = lambda js: [first, second, third]

    rows = _rows(_expect_dashboard(session))

    assert len(rows) == 1 and "hun" not in rows[0].path


def test_f5_secret_with_consecutive_whitespace_is_scrubbed(tmp_path: Path) -> None:
    session = session_with_fake_page(tmp_path)
    (tmp_path / ".env").write_text('PATHLYNKS_PASSWORD="pass  word  9"' + chr(10), encoding="utf-8")
    session.secrets = SecretStore.load(make_project(), tmp_path / ".env")
    session.page.body_text = "Sign in"
    # the in-page extractor collapses whitespace, so the secret reaches Python with single spaces
    session.page.evaluate = lambda js: ["Wrong credential pass word 9 for this account"]

    rows = _rows(_expect_dashboard(session))

    assert len(rows) == 1
    assert "pass word 9" not in rows[0].path and "word" not in rows[0].path
