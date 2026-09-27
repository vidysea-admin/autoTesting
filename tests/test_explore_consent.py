"""The crawl consent pre-flight (`stages/explore_consent.py`).

AT-535 (X10-b condition 3): a synthetic-typing run covered by a production
approval is refused BEFORE the browser opens — D-029's four conditions are
enforced where the run begins, and the refusal names the approval's id. The
base capability is untouched: the same approval still covers an ordinary
READ_ONLY crawl, and a dev-environment approval covers typing.

Contract: qa/contracts/explore.md X10-b (condition 3), qa/contracts/coverage.md
(no coverage claim); gate: qa/gates/live-crawl-target.md (Pathlynks dev).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from crawl_fake import make_project

from autotester.schema.approval import RunApproval
from autotester.schema.crawl import CrawlBounds, SafetyPolicy
from autotester.schema.enums import ApprovalKind, WritePolicy
from autotester.store.project_store import ProjectStore

TYPED_POLICY = SafetyPolicy(write_policy=WritePolicy.TEST_ACCOUNT, synthetic_typing=True)
READ_ONLY_POLICY = SafetyPolicy(write_policy=WritePolicy.READ_ONLY)


def _store_with(tmp_path: Path, production: bool) -> tuple[ProjectStore, object]:
    project = make_project(WritePolicy.TEST_ACCOUNT)
    store = ProjectStore("demo", tmp_path)
    bounds = CrawlBounds()
    store.add_approval(RunApproval(
        project=project.slug, run_kind=ApprovalKind.CRAWL, target=project.base_url,
        scope="production crawl" if production else "dev-environment crawl",
        max_actions=bounds.max_actions, wall_clock_s=bounds.wall_clock_s,
        granted_by="test", granted_at="2026-09-21", expires_at="2099-01-01",
        production=production,
    ).sign())
    return store, project


def test_typing_is_refused_against_a_production_approval(tmp_path: Path) -> None:
    from autotester.core.consent import ApprovalRequired
    from autotester.stages.explore_consent import require_consent

    store, project = _store_with(tmp_path, production=True)
    with pytest.raises(ApprovalRequired, match="synthetic typing"):
        require_consent(project, store, CrawlBounds(), policy=TYPED_POLICY)


def test_the_same_approval_still_covers_an_ordinary_read_only_crawl(
    tmp_path: Path,
) -> None:
    """Condition 3 narrows TYPING runs only — the base capability is unchanged."""
    from autotester.stages.explore_consent import require_consent

    store, project = _store_with(tmp_path, production=True)
    require_consent(project, store, CrawlBounds(), policy=READ_ONLY_POLICY)


def test_typing_runs_against_a_dev_approval(tmp_path: Path) -> None:
    """The happy path the Pathlynks stage-2 crawl will use: TEST_ACCOUNT policy
    + synthetic_typing + a production:false approval — consent holds."""
    from autotester.stages.explore_consent import require_consent

    store, project = _store_with(tmp_path, production=False)
    require_consent(project, store, CrawlBounds(), policy=TYPED_POLICY)