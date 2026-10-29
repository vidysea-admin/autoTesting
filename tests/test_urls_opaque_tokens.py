"""`core.urls.url_template` templates opaque path tokens (JWT, email, base64, matrix params,
prefixed order ids) while every plain word segment keeps its exact template, so no stored
screen id drifts. The drift proof walks every committed crawl/flow fixture URL.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from autotester.core.urls import url_template

_ROOT = Path(__file__).resolve().parent.parent
_JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk"
_B64 = "Zm9vYmFyQmF6MTIzNDU2Nzg5MEFiQ2Q"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (f"/api/auth/verify/{_JWT}", "/api/auth/verify/{token}"),
        ("/api/users/john.doe@example.com/profile", "/api/users/{email}/profile"),
        ("/api/users/john.doe%40example.com/profile", "/api/users/{email}/profile"),
        (f"/api/invite/{_B64}", "/api/invite/{token}"),
        ("/api/invite/Zm9vYmFyQmF6MTIzNDU2Nzg5MA==", "/api/invite/{token}"),
        ("/api/session;jsessionid=ABC123DEF456", "/api/session"),
        ("/api/session;jsessionid=ABC123DEF456/orders", "/api/session/orders"),
        ("/orders/ORD-2024-00081", "/orders/{id}"),
        ("/invoices/INV-00081/pay", "/invoices/{id}/pay"),
        ("/projects/p/crawls/crawl_01M3SPT02KH34KF61NYK8P1VBZ", "/projects/p/crawls/{id}"),
        ("/customers/cus_0123456789abcdef0123", "/customers/{id}"),
        ("https://x.test/api/users/a@b.io", "x.test/api/users/{email}"),
    ],
)
def test_opaque_tokens_are_templated(url: str, expected: str) -> None:
    assert url_template(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "/dashboard", "/messages", "/settings/profile", "/students/me", "/reports/summary",
        "/covid-19", "/class-12/notes", "/top-10", "/year-2024", "/FY-2024", "/q3-2024-report",
        "/introduction-to-python-3-programming-basics", "/internationalbusinessadministration",
        "/Introduction-to-Python-3-Programming", "/docs/v1.2/guide", "/sign-in", "/api/v2/users",
        "/file.name.with.dots", "/UPPERCASE", "/ABC-DEF", "/users/me@", "/a@b", "/{id}/{token}",
    ],
)
def test_plain_word_segments_keep_the_exact_template(url: str) -> None:
    assert url_template(url, keep_host=False) == url


def test_placeholders_are_stable_when_re_templated() -> None:
    once = url_template(f"/x/{_JWT}/a@b.io/ORD-2024-00081/{_B64}", keep_host=False)
    assert once == "/x/{token}/{email}/{id}/{token}"
    assert url_template(once, keep_host=False) == once


def test_query_and_fragment_secrets_still_never_reach_the_template() -> None:
    assert url_template(f"/api/a?t={_JWT}#{_B64}", keep_host=False) == "/api/a"


def test_a_matrix_only_segment_is_dropped_not_left_empty() -> None:
    assert url_template("/api/;jsessionid=ABC/orders", keep_host=False) == "/api/orders"


# --- drift proof over committed fixtures ---------------------------------------------------

_URL_KEYS = re.compile(r"^(url|url_template|url_pattern|url_example|target_url|start_url|page)$")
_FIXTURE_DIRS = ("projects", "tests/fixtures", "qa", "docs")


def _legacy(url: str) -> str:
    """Frozen copy of the pre-change normaliser (keep_host=False, fold_index=True)."""
    num, hexid = re.compile(r"^\d+$"), re.compile(r"^[0-9a-f]{16,}$", re.I)
    uuid = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
    ulid, date = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$"), re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
    segs = [s for s in urlsplit(url).path.split("/") if s]
    if segs and segs[-1] in {"index.html", "index.htm"}:
        segs = segs[:-1]

    def one(s: str) -> str:
        if date.match(s):
            return "{date}"
        return "{id}" if any(p.match(s) for p in (num, uuid, ulid, hexid)) else s

    return "/" + "/".join(one(s) for s in segs) if segs else "/"


def _walk(node: object, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, val in node.items():
            if isinstance(val, str) and _URL_KEYS.match(key) and val.strip():
                out.append(val)
            else:
                _walk(val, out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, out)


def _fixture_urls() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for base in _FIXTURE_DIRS:
        for path in sorted((_ROOT / base).rglob("*.json*")):
            if ".work" in path.parts or "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            docs = text.splitlines() if path.suffix == ".jsonl" else [text]
            for doc in docs:
                try:
                    values: list[str] = []
                    _walk(json.loads(doc), values)
                except ValueError:
                    continue
                found.extend((str(path.relative_to(_ROOT)), v) for v in values)
    return found


_CRAWL_ID = re.compile(r"crawl_[0-9A-HJKMNP-TV-Z]{26}")


def _changed() -> dict[tuple[str, str], tuple[str, str]]:
    return {
        (rel, raw): (_legacy(raw), url_template(raw, keep_host=False, fold_index=True))
        for rel, raw in _fixture_urls()
        if raw.startswith(("/", "http"))
        and _legacy(raw) != url_template(raw, keep_host=False, fold_index=True)
    }


def test_no_committed_project_or_site_fixture_url_changes_template() -> None:
    """projects/*/ crawl and flow fixtures and tests/fixtures/ sites: zero drift."""
    assert _fixture_urls(), "expected committed fixture urls to walk"
    moved = {k: v for k, v in _changed().items() if k[0].startswith(("projects", "tests"))}
    assert not moved, moved


def test_the_only_template_changes_anywhere_are_crawl_ids_in_qa_evidence() -> None:
    """qa/evidence records AutoTester's own UI urls: `/projects/p/crawls/crawl_<ULID>` -> `{id}`."""
    for (rel, raw), (old, new) in _changed().items():
        assert rel.startswith("qa"), (rel, raw)
        assert _CRAWL_ID.sub("{id}", old) == new, (raw, old, new)
