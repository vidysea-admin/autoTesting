"""Grant a real `RunApproval` covering a UI case run (AT-570).

One job: the "grant it, never bypass the gate" helper the run-trigger tests
share, now that `POST /projects/{slug}/run` requires an
`ApprovalKind.LIVE_CASE` approval the same way a crawl already requires a
`CRAWL` one. Not a test module -- pytest does not collect it.

Deliberately NOT added to `crawl_fake.py` (that module imports the explorer, a
real `BrowserSession` and a `PageObserver`, none of which a UI run test wants
to pull in) and deliberately not copied into each of the run-trigger test
files, which would be C3's one-concept-two-places.
"""

from __future__ import annotations

from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind
from autotester.store.project_store import ProjectStore


def grant_live_case_approval(
    store: ProjectStore, *, project: str = "demo", target: str = "https://demo.test",
    max_actions: int = 10_000, max_probes: int = 0, wall_clock_s: float = 100_000.0,
    sign: bool = True, expires_at: str = "2099-01-01",
    run_kind: ApprovalKind = ApprovalKind.LIVE_CASE,
) -> RunApproval:
    """Add one unexpired, signed `live_case` approval wide enough for the run.

    **The bounds are deliberately non-zero** (AT-660): a 0-bound fixture passes
    the gate AND enforces nothing, so a test built on one would assert "an
    approved run proceeds" for the wrong reason and could not express an
    over-budget refusal at all (`0 > 0` is false, so there is no over-budget to
    construct). Callers that want a refusal pass a real small bound instead.

    `max_probes` is the ONE bound left at 0 here, and it is passed explicitly
    rather than inherited from the model default so the choice is visible: a
    case run spends actions, never probes (`stages/parallel_run.py::_run_one`
    consumes `action_cost(case)` and nothing else), so a non-zero probe grant
    would be a bound on something this path cannot spend. This is also the exact
    shape every UI-granted approval has -- the grant form carries no
    `max_probes` field at all (AT-675) -- so the fixture matches what an
    operator can actually produce.

    `sign=False` writes the UNSIGNED shape every row in
    `projects/pathlynks/approvals.jsonl` actually has on disk today, so a test
    can exercise the refusal an operator will really meet rather than a
    hypothetical one. `run_kind` is a parameter so a test can grant the WRONG
    kind (a `crawl` row) and show it does not cover a case run.
    """
    approval = RunApproval(
        project=project, run_kind=run_kind, target=target,
        scope="fixture case run in tests", max_actions=max_actions,
        max_probes=max_probes, wall_clock_s=wall_clock_s,
        granted_by="test", granted_at="2026-09-28",
        expires_at=expires_at,
    )
    if sign:
        approval.sign()
    store.add_approval(approval)
    return approval


def project_of(slug, *, production: bool = False):
    """A minimal `Project` for gate tests (unvalidated; a `Project` passes through)."""
    from autotester.schema.project import Project
    if isinstance(slug, Project):
        return slug
    return Project.model_construct(slug=slug, name="x", base_url="https://llm.test/",
                                   allowed_domains=["llm.test"], production=production)
