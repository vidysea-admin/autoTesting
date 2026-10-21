"""AT-1349: crawl.json never carries a raw secret (holes keep page text, link names, hrefs).

Offline: the fake site, a temp dir, no browser, network or model. The secret is a .env value, so
the session Redactor knows it (AT-004), exactly as in a live run.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from crawl_fake import BASE, SITE, grant_crawl_approval, make_project, make_session

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.core.paths import ProjectPaths
from autotester.core.redact import MASK
from autotester.schema.crawl import CoverageHole, Crawl, CrawlBounds, CrawlCoverage, NoiseCount
from autotester.stages import explore
from autotester.stages import explore_summary as persisted
from autotester.store.project_store import ProjectStore

SECRET = "hunter2-Zq9-reset-token"


def _hole(**over) -> CoverageHole:
    fields = {"node_id": "node_a", "url_template": "/reset", "selector": "a.x", "name": "Go",
              "reason": "policy:deny"}
    return CoverageHole(**{**fields, **over})


def _rt(tmp_path: Path) -> SimpleNamespace:
    project = make_project()
    session = make_session(tmp_path, project)[0]
    (tmp_path / ".env").write_text(f"AUTOTESTER_RESET_TOKEN={SECRET}\n", encoding="utf-8")
    session.secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    return SimpleNamespace(session=session, store=ProjectStore("demo", tmp_path))


def test_a_secret_in_a_link_name_and_an_href_is_absent_from_the_written_crawl_json(
    tmp_path: Path,
) -> None:
    """C1: the save path masks every hole field (name, selector, url_template), keeps the hole."""
    rt = _rt(tmp_path)
    holes = [_hole(name=f"Reset password for {SECRET}", selector=f"a[href*='{SECRET}']",
                   url_template=f"/reset/{SECRET}")]
    coverage = CrawlCoverage(holes=holes, screens_not_entered=[_hole(name=SECRET)],
                             permitted_holes=[_hole(selector=SECRET)], error=f"boom {SECRET}")
    crawl = Crawl(project="demo", coverage=coverage, stop_reason=f"stopped at {SECRET}",
                  noise_counts=[NoiseCount(host=f"{SECRET}.cdn.test", count=2)])
    persisted.save_crawl(rt, crawl)
    text = rt.store.paths.crawl_manifest(crawl.id).read_text(encoding="utf-8")
    assert SECRET not in text
    on_disk = json.loads(text)
    hole = on_disk["coverage"]["holes"][0]
    assert MASK in hole["name"] and MASK in hole["selector"] and MASK in hole["url_template"]
    assert hole["node_id"] == "node_a" and hole["reason"] == "policy:deny"
    assert len(on_disk["coverage"]["screens_not_entered"]) == 1
    assert crawl.coverage.holes[0].name.endswith(SECRET)  # memory keeps the real value


def test_a_real_crawl_with_a_secret_named_control_persists_a_masked_hole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C1 end to end: run_crawl -> _finish -> crawl.json; the denied control is still a hole."""
    monkeypatch.setitem(SITE, BASE, [
        {"role": "button", "name": f"Delete account {SECRET}", "selector": f"button.del-{SECRET}"},
        {"role": "link", "name": f"Leave {SECRET}", "selector": "a.ext",
         "href": f"https://evil.test/?k={SECRET}"},
    ])
    project = make_project()
    session, _page = make_session(tmp_path, project)
    (tmp_path / ".env").write_text(f"AUTOTESTER_RESET_TOKEN={SECRET}\n", encoding="utf-8")
    session.secrets = SecretStore.load(project, tmp_path / ".env", strict=False)
    store = ProjectStore("demo", tmp_path)
    grant_crawl_approval(store, project)
    crawl = explore.run_crawl(project, session, store, observer=PageObserver(),
                              bounds=CrawlBounds())
    text = ProjectPaths("demo", tmp_path).crawl_manifest(crawl.id).read_text(encoding="utf-8")
    assert SECRET not in text
    holes = store.load_crawl(crawl.id).coverage.holes
    assert holes and any(MASK in h.name or MASK in h.selector for h in holes)


def test_a_numeric_secret_does_not_corrupt_the_crawl_envelope_ids_or_timestamps(
    tmp_path: Path,
) -> None:
    """C2: the unit keeps the crawl-redact-timestamp rule: minted ids and typed times survive."""
    rt = _rt(tmp_path)
    (tmp_path / ".env").write_text("AUTOTESTER_SMTP_PORT=587\n", encoding="utf-8")
    rt.session.secrets = SecretStore.load(make_project(), tmp_path / ".env", strict=False)
    crawl = Crawl(id="crawl_587", project="demo", started_at="2026-10-19T05:58:07.587000Z",
                  coverage=CrawlCoverage(holes=[_hole(node_id="node_587a", name="Port 587")]))
    persisted.save_crawl(rt, crawl)
    back = rt.store.load_crawl("crawl_587")
    assert back.id == "crawl_587" and back.started_at == crawl.started_at
    hole = back.coverage.holes[0]
    assert hole.node_id == "node_587a" and "587" not in hole.name
