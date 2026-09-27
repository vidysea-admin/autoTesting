"""What `autotester approve` ACTUALLY does — the command that GRANTS consent.

Split from `test_crawl_real_cli.py` at the 300-line cap, by responsibility:
that file is about refusing a crawl, this one is about issuing the approval
that permits one. `approve` had no test at all until AT-140, while the refusal
path around it was well defended — the gate's *deny* half was guarded and its
*grant* half was not.

Contract: qa/contracts/consent.md CN5-CN7.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from autotester.cli import app
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore

runner = CliRunner()

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
BASE_URL = "https://demo.test/"
CLI_DEFAULT_ACTIONS = 200
CLI_DEFAULT_WALL_CLOCK = "600.0"


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url=BASE_URL,
                               allowed_domains=["demo.test"]))
    return tmp_path


def grant(*extra: str) -> object:
    return runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "read-only crawl", "--granted-by", "umesh",
        "--expires", TOMORROW, *extra,
    ])


# -- `approve`, the command that grants consent ----------------------------

def test_approve_writes_a_row_that_covers_the_cli_defaults(root: Path) -> None:
    """An approval for exactly the default action budget must let the default
    run through.

    AT-146 -- I originally called this "the one row I would keep", claiming it
    pins `explore_cmd`'s TYPER defaults to `require_consent`. It does not: it
    never invokes `explore`, it constructs `CrawlBounds()` directly, so it pins
    the SCHEMA defaults. The checker proved it by drifting the typer default
    200 -> 137, under which this test still passed. What actually protects that
    seam is the two refusal tests above, which read the bounds out of the real
    command's output. Kept, correctly described."""
    from autotester.schema.crawl import CrawlBounds
    from autotester.stages.explore_consent import require_consent

    assert grant("--max-actions", str(CLI_DEFAULT_ACTIONS),
                 "--wall-clock", CLI_DEFAULT_WALL_CLOCK).exit_code == 0

    store = ProjectStore("demo", root)
    proj = store.load_project()
    require_consent(proj, store, CrawlBounds())  # must not raise


def test_an_approval_narrower_than_the_run_still_refuses(root: Path) -> None:
    """One action short. A gate that only fails when the approval is ABSENT is
    a gate that never checks its own bounds."""
    from autotester.core.consent import ApprovalRequired
    from autotester.schema.crawl import CrawlBounds
    from autotester.stages.explore_consent import require_consent

    assert grant("--max-actions", str(CLI_DEFAULT_ACTIONS - 1),
                 "--wall-clock", CLI_DEFAULT_WALL_CLOCK).exit_code == 0

    store = ProjectStore("demo", root)
    with pytest.raises(ApprovalRequired):
        require_consent(store.load_project(), store, CrawlBounds())


def test_approve_rejects_an_unknown_kind_and_names_the_valid_ones(root: Path) -> None:
    result = runner.invoke(app, [
        "approve", "demo", "--kind", "definitely-not-a-kind", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", TOMORROW,
    ])

    assert result.exit_code == 1
    assert "crawl" in result.output and "adversarial" in result.output


def test_approve_on_an_unknown_project_exits_one(root: Path) -> None:
    result = runner.invoke(app, [
        "approve", "nope", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", TOMORROW,
    ])

    assert result.exit_code == 1
    assert "no project" in result.output


# -- AT-145: a grant that cannot cover anything must say so ---------------

def test_approve_refuses_an_already_expired_date(root: Path) -> None:
    """AT-145: `approve --expires 2020-01-01` exited 0 with a green "granted"
    line. The safety property held — `require_consent` refuses an expired row
    — but the human granting T-145's PRODUCTION consent was told it worked.
    A gate that reports success for a grant it will never honour trains the
    operator to ignore it."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", yesterday,
    ])

    assert result.exit_code == 1
    assert "already" in result.output.lower() or "past" in result.output.lower()


def test_approve_refuses_an_unparseable_expiry(root: Path) -> None:
    """`--expires never` was accepted verbatim and stored, where it can only
    ever compare as "not today's date"."""
    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", "never",
    ])

    assert result.exit_code == 1
    assert "YYYY-MM-DD" in result.output


def test_approve_grants_an_expiry_of_today(root: Path) -> None:
    """AT-147, high, and the date an operator granting SAME-DAY production
    consent for T-145 would actually type.

    `_validate_grant` compared `< date.today()` while `RunApproval.is_expired`
    reads a bare date through `fromisoformat` — i.e. MIDNIGHT — so an approval
    "expiring today" was already dead at 00:00:01. `approve` printed a green
    granted line; the very next `explore` refused it as `expired`.

    **Updated for CN4 (at147 answered C, D-048):** a NEW grant no longer stores
    the bare date at all — `approve_cmd` now stores an explicit end-of-day
    timestamp, so `--expires <today>` is GRANTED and honoured through the rest
    of today. The old contradiction is gone because the grant and the runtime
    now agree on what "today" means, not because either moved to match the
    other's mistake. The exact boundary is pinned, timezone-independently, by
    `test_a_new_grant_is_honoured_through_the_end_of_its_day_and_refused_one_second_later`
    below."""
    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", date.today().isoformat(),
    ])

    assert result.exit_code == 0
    assert date.today().isoformat() in result.output


def test_the_grant_and_the_runtime_agree_on_every_expiry_they_accept(
    root: Path,
) -> None:
    """The real property behind AT-145 and AT-147, stated once: any expiry
    `approve` ACCEPTS must be one `require_consent` will HONOUR. The two used
    different comparisons, so there was a whole day where they disagreed."""
    from autotester.schema.crawl import CrawlBounds
    from autotester.stages.explore_consent import require_consent

    for offset in (1, 2, 30):
        when = (date.today() + timedelta(days=offset)).isoformat()
        assert grant("--max-actions", str(CLI_DEFAULT_ACTIONS),
                     "--wall-clock", CLI_DEFAULT_WALL_CLOCK,
                     "--expires", when).exit_code == 0, f"{when} was refused at grant"

        store = ProjectStore("demo", root)
        require_consent(store.load_project(), store, CrawlBounds())  # must not raise


def test_the_expiry_refusal_prints_a_usable_date(root: Path) -> None:
    """AT-150: the refusal said the operator needs "tomorrow's date" and never
    printed one. My own test asserted only that the word "tomorrow" appeared,
    so a refusal naming no usable date would have passed it — a test written
    against the message I meant rather than the message a reader gets.

    **Updated for CN4 (at147 answered C, D-048):** `--expires <today>` is no
    longer refused (`test_approve_grants_an_expiry_of_today`), so this drives
    the one branch that remains — a genuinely PAST date — and the usable date
    it must now print is TODAY, since today is the earliest day a new grant
    can still cover."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", yesterday,
    ])

    assert result.exit_code == 1
    assert date.today().isoformat() in result.output, "the refusal must name a date, not a word"


# -- AT-151 / AT-152: one arm fixed, the other forgotten (again) -----------

def test_a_past_expiry_also_names_a_usable_date(root: Path) -> None:
    """AT-151: the AT-150 fix named a usable date on the `today` branch and not
    on the `past` one. That is the AT-149 pattern a THIRD time -- fixing one arm
    of a two-arm condition and leaving its twin. CN4 requires the refusal to
    name a usable date unqualified, not on the branch I happened to test.

    **Updated for CN4 (at147 answered C, D-048):** there is now only one arm
    (`expiry < today`), so this test and `test_the_expiry_refusal_prints_a_usable_date`
    exercise it at two different distances into the past — kept as two tests
    because AT-151's own lesson is that one distance is not enough evidence an
    arm generalises. The usable date is TODAY now, not tomorrow."""
    long_ago = (date.today() - timedelta(days=400)).isoformat()

    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", long_ago,
    ])

    assert result.exit_code == 1
    assert date.today().isoformat() in result.output, "the past branch names no usable date"


# -- at147 answered C (D-048): end-of-day for NEW grants only --------------

def test_a_new_grant_is_honoured_through_the_end_of_its_day_and_refused_one_second_later(
    root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CN4: a NEW grant's expiry is stored offset-aware in local time, e.g.
    `2026-09-26T23:59:59+05:30` — never naive, or `RunApproval.is_expired`
    would read it as UTC and shift the boundary by the host's own offset.
    `cli_crawl._local_now` is the single seam monkeypatched here, so this pins
    an exact instant regardless of the machine's real clock or timezone."""
    import autotester.cli_crawl as cli_crawl_mod
    from autotester.core.consent import ApprovalRequired, require_approval
    from autotester.schema.enums import ApprovalKind

    tz = timezone(timedelta(hours=5, minutes=30))
    fixed_now = datetime(2026, 9, 26, 10, 0, 0, tzinfo=tz)
    monkeypatch.setattr(cli_crawl_mod, "_local_now", lambda: fixed_now)

    result = runner.invoke(app, [
        "approve", "demo", "--kind", "crawl", "--target", BASE_URL,
        "--scope", "s", "--granted-by", "umesh", "--expires", "2026-09-26",
        "--max-actions", str(CLI_DEFAULT_ACTIONS), "--wall-clock", CLI_DEFAULT_WALL_CLOCK,
    ])
    assert result.exit_code == 0

    store = ProjectStore("demo", root)
    approval = store.list_approvals()[0]
    assert approval.expires_at == "2026-09-26T23:59:59+05:30", (
        "must be offset-aware end-of-day local time, never a naive stamp"
    )

    last_local_second = datetime(2026, 9, 26, 23, 59, 59, tzinfo=tz)
    one_second_later = datetime(2026, 9, 27, 0, 0, 0, tzinfo=tz)

    covering = require_approval(
        [approval], project="demo", kind=ApprovalKind.CRAWL, target=BASE_URL,
        actions=CLI_DEFAULT_ACTIONS, wall_clock_s=float(CLI_DEFAULT_WALL_CLOCK),
        now=last_local_second,
    )
    assert covering.id == approval.id

    with pytest.raises(ApprovalRequired):
        require_approval(
            [approval], project="demo", kind=ApprovalKind.CRAWL, target=BASE_URL,
            actions=CLI_DEFAULT_ACTIONS, wall_clock_s=float(CLI_DEFAULT_WALL_CLOCK),
            now=one_second_later,
        )
