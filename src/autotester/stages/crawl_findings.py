"""Turn a project's recorded crawl issues into bench `Finding`s (T-136 route (b)).

One job: the converter. A crawl already records first-party failed requests and console
errors as `CrawlIssue`s (`stages/explore_node.py::add_issue`); until now none of them reached
the acceptance comparison, so a run with no FAIL verdict reported 0 findings. Here the product
faults among them become findings with `source="crawl"`, deduplicated by kind + URL + status
(or console text), each carrying the paths of the recorded evidence.

Not product faults, so never findings (X9: filing a tool failure as a product bug is the
dishonesty the crawl contract forbids): EVIDENCE (the crawler failed), third-party noise,
and the crawler's own state (NAVIGATION lost-screen, OVERLAY, DIALOG storms). Console
warnings are noise; only `error:` lines count. Nothing is scored here (bench.md K3).
"""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlsplit, urlunsplit

from autotester.schema.bench import Finding
from autotester.schema.crawl import CrawlIssue
from autotester.schema.enums import IssueKind
from autotester.schema.screen_graph import ScreenNode
from autotester.store.project_store import ProjectStore

NodeIndex = Mapping[tuple[str, str], ScreenNode]


class CrawlNotFound(Exception):
    """A named crawl has no stored directory; no numbers are invented."""


def _bare(url: str) -> str:
    """The URL without query or fragment: ids and tokens ride there, and they split a dedup."""
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _network_key(issue: CrawlIssue) -> tuple[str, str] | None:
    url, sep, why = issue.detail.partition(" -> ")
    if not sep or not url.strip():
        return None
    return _bare(url), why.strip() or "failed"


def _console_key(issue: CrawlIssue) -> str | None:
    text = " ".join(issue.detail.split())
    return text if text.lower().startswith("error") else None


def _dedup_key(issue: CrawlIssue) -> tuple[str, ...] | None:
    """The identity of a product fault, or None when the issue is not a product fault."""
    if not issue.first_party:
        return None
    if issue.kind is IssueKind.NETWORK:
        key = _network_key(issue)
        return None if key is None else ("network", *key)
    if issue.kind is IssueKind.CONSOLE:
        text = _console_key(issue)
        return None if text is None else ("console", text)
    return None


def _text(key: tuple[str, ...], seen: int, screens: int) -> str:
    where = f"seen {seen}x on {screens} screen(s)"
    if key[0] == "network":
        return f"crawl: first-party request {key[1]} failed with {key[2]} ({where})"
    return f"crawl: console {key[1]} ({where})"


def _evidence(group: list[CrawlIssue], nodes: NodeIndex) -> list[str]:
    """Per crawl: the recorded issue row, plus the screen's screenshot when it has one."""
    refs: list[str] = []
    done: set[str] = set()
    for issue in group:
        if issue.crawl_id in done:
            continue
        done.add(issue.crawl_id)
        refs.append(f"crawl/{issue.crawl_id}/issues.jsonl#{issue.id}")
        node = nodes.get((issue.crawl_id, issue.node_id))
        if node is not None and node.screenshot_ref:
            refs.append(f"crawl/{issue.crawl_id}/shots/{node.screenshot_ref}")
    return refs


def findings_from_crawl_issues(issues: list[CrawlIssue], nodes: NodeIndex) -> list[Finding]:
    """One `Finding(source="crawl")` per distinct product fault; first-seen order."""
    groups: dict[tuple[str, ...], list[CrawlIssue]] = {}
    for issue in issues:
        key = _dedup_key(issue)
        if key is not None:
            groups.setdefault(key, []).append(issue)
    return [
        Finding(
            text=_text(key, len(group), len({(i.crawl_id, i.node_id) for i in group})),
            matched_bug_id=None, evidence_refs=_evidence(group, nodes), source="crawl",
        )
        for key, group in groups.items()
    ]


def crawl_findings_for(store: ProjectStore, crawl_ids: list[str]) -> list[Finding]:
    """Convert every named crawl's recorded issues; refuse a crawl that is not stored."""
    stored = set(store.list_crawl_ids())
    missing = [c for c in crawl_ids if c not in stored]
    if missing:
        raise CrawlNotFound(f"crawl {', '.join(missing)} not found under {store.paths.crawls_dir}")
    issues: list[CrawlIssue] = []
    nodes: dict[tuple[str, str], ScreenNode] = {}
    for crawl_id in crawl_ids:
        issues.extend(store.list_crawl_issues(crawl_id))
        nodes.update({(crawl_id, n.id): n for n in store.list_nodes(crawl_id)})
    return findings_from_crawl_issues(issues, nodes)

