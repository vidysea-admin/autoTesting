"""Which collection and which store area a state key belongs to (mongo-store M15, M21, M22; D-122).

One job: the key -> (collection, area, rows-or-document) table the Mongo backend and the area
selection both read, plus the helpers that must agree across every backend (digest, row match,
segment-boundary prefix, immediate children, the knowledge-graph split). Pure data and string
logic, and the `StateBackend` contract every backend implements: no driver is imported, so a
file-mode process loads it without `pymongo` (M13).
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterable
from fnmatch import fnmatchcase
from functools import cache
from typing import NamedTuple, Protocol

from autotester.core.env import MONGO_URI_ENV, mongo_uri, read_dotenv, redaction_values
from autotester.core.paths import repo_root
from autotester.core.redact import Redactor
from autotester.core.safe_names import UnsafeName

AREAS = ("settings", "projects", "runs", "crawls", "approvals", "auth", "credentials", "blobs",
         "queue")
BACKENDS = ("file", "mongo")
UNROUTED: dict[str, str] = {}
"""Areas whose data never travels through a state key: flipping one would route nothing."""
RUN_AUX_FILES = frozenset({
    "run.json", "ux_report.json", "state.json", "checkpoint.json", "scope.json", "release.json",
    "ingest.flowspec.json", "discover.flowspec.json",  # T-169: parked proposals
    "teaching-inputs.json", "teaching.json",  # Mixed teaching evidence and proposal
})
"""Non-result JSON files that sit in a run dir. `load_results` skips exactly these; any other
unreadable JSON there still fails loudly, as before."""
KG_COLLECTIONS = ("kg_nodes", "kg_edges")
KG_SPLIT_BYTES = 4 * 1024 * 1024
PERSONA_SUFFIX = "/portal_persona.json"
OTHER_UNITS = {  # collections in the guard's closed set that no state key reaches
    **dict.fromkeys(("auth_users", "auth_groups", "auth_sessions", "auth_grants", "auth_meta",
                     "video_shares", "video_links", "access_requests", "video_comments"), "U6"),
    **dict.fromkeys(("secrets",), "U11"), **dict.fromkeys(("browser_sessions",), "U12"),
}

# (pattern, collection, area). `*` matches inside one segment; a last `**` matches one or more.
_RULES: tuple[tuple[str, str, str], ...] = (
    ("projects/*/project.json", "projects", "projects"),
    ("projects/*/sources.jsonl", "sources", "projects"),
    ("projects/*/sources/*/media.json", "source_media", "projects"),
    ("projects/*/sources/**", "source_docs", "projects"),
    ("projects/*/cases.jsonl", "cases", "projects"),
    ("projects/*/case_proposals.jsonl", "case_proposals", "projects"),
    ("projects/*/rubrics/**", "rubrics", "projects"),
    ("projects/*/issues.jsonl", "issues", "projects"),
    ("projects/*/requests.jsonl", "requests", "projects"),
    ("projects/*/user_personas.jsonl", "user_personas", "projects"),
    ("projects/*/flow_plans.jsonl", "flow_plans", "projects"),
    ("projects/*/approvals.jsonl", "approvals", "approvals"),
    ("projects/*/approval_revocations.jsonl", "approval_revocations", "approvals"),
    ("projects/*/bench/**", "bench_docs", "projects"),
    ("projects/*/bug_events/**", "bug_events", "projects"),
    ("projects/*/bug_loop_config.json", "bug_config", "projects"),
    ("projects/*/scripts/**", "scripts", "projects"),
    ("projects/*/reviews/**", "reviews", "projects"),
    ("projects/*/ai/**", "ai_docs", "projects"),
    ("projects/*/runs/*/trace.jsonl", "run_traces", "runs"),
    ("projects/*/runs/*/bundles/**", "bundles", "runs"),
    ("projects/*/runs/*/run.json", "runs", "runs"),
    ("projects/*/runs/*/*.verdict.json", "run_verdicts", "runs"),
    ("projects/*/runs/*/*.json", "run_results", "runs"),  # aux names are re-routed in `route`
    ("projects/*/runs/**", "run_docs", "runs"),
    ("projects/*/crawl/*/crawl.json", "crawls", "crawls"),
    ("projects/*/crawl/*/nodes.jsonl", "crawl_nodes", "crawls"),
    ("projects/*/crawl/*/edges.jsonl", "crawl_edges", "crawls"),
    ("projects/*/crawl/*/issues.jsonl", "crawl_issues", "crawls"),
    ("projects/*/crawl/*/network.jsonl", "crawl_network", "crawls"),
    ("projects/*/crawl/**", "crawl_docs", "crawls"),
    ("projects/*/crawl_summaries/**", "crawl_summaries", "crawls"),
    ("projects/**", "project_docs", "projects"),
    (".work/run_queue.json", "server_state", "queue"),
    (".work/notification_prefs/**", "notification_prefs", "settings"),
    (".work/audit.jsonl", "audit_log", "settings"),
    (".work/drive-jobs/**", "drive_jobs", "settings"),
    (".work/team/schedule/claims/**", "schedule_claims", "queue"),
    (".work/team/schedule/*.jsonl", "schedule_records", "queue"),
    (".work/team/schedule/**", "server_state", "queue"),
    (".work/team/delivery/**", "delivery_records", "queue"),
    ("**", "server_state", "settings"),
)
_SPLIT = tuple((tuple(pattern.split("/")), coll, area) for pattern, coll, area in _RULES)
ROUTED_COLLECTIONS = frozenset({c for _, c, _ in _RULES} | {"run_results", *KG_COLLECTIONS})


class StateBackend(Protocol):
    """Keys: relative POSIX paths. Rows: ordered JSON lines. Each method runs `safe_key` first."""

    def get(self, key: str) -> str | None: ...
    def put(self, key: str, data: str | bytes) -> None: ...
    def put_if(self, key: str, text: str, expect_sha: str | None) -> bool: ...
    def create_exclusive(self, key: str, text: str) -> bool: ...
    def delete(self, key: str) -> bool: ...
    def exists(self, key: str) -> bool: ...
    def keys(self, prefix: str, suffix: str = "") -> list[str]: ...
    def delete_prefix(self, prefix: str) -> int: ...
    def rows(self, key: str) -> list[str]: ...
    def append_row(self, key: str, text: str) -> None: ...
    def append_text(self, key: str, text: str) -> None: ...
    def upsert_row(self, key: str, field: str, value: str, text: str) -> None: ...
    def delete_row(self, key: str, field: str, value: str) -> bool: ...
    def replace_rows(self, key: str, rows: list[str]) -> None: ...
    def ping(self) -> None: ...
    def children(self, key: str, suffix: str = "") -> list[str]: ...
    def is_dir(self, key: str) -> bool: ...
    def mtime(self, key: str) -> float | None: ...


class StoreSelectionError(ValueError):
    """`AUTOTESTER_STORE` / `AUTOTESTER_STORE_AREAS` names something unknown or not wired."""


class StoreDown(RuntimeError):
    """Driver-free base of `mongo_guard.StoreUnavailable`: the UI maps it to 503 (M26) without
    importing a driver in file mode (M13)."""


class StoreImmutable(RuntimeError):
    """A replace, update or delete was asked of an insert-only collection (M7, D-018)."""


class StoreDocTooLarge(ValueError):
    """A document over `MAX_DOC_BYTES`: refused, never truncated (M18)."""


class StoreSecretRefused(ValueError):
    """The text carries a known secret value, so nothing was written (M8). Never quotes it."""


class Route(NamedTuple):
    collection: str
    area: str
    rows: bool  # a `.jsonl` key is an ordered set of rows; any other key is one document
    project: str  # the project slug the key sits under, else ""


def _fits(pattern: tuple[str, ...], segments: list[str]) -> bool:
    if pattern[-1] == "**":
        head = pattern[:-1]
        return len(segments) > len(head) and all(map(fnmatchcase, segments, head))
    return len(pattern) == len(segments) and all(map(fnmatchcase, segments, pattern))


@cache
def route(key: str) -> Route:
    """The first rule that fits `key`. A run-dir file named in `RUN_AUX_FILES` is a run document."""
    segments = key.split("/")
    for pattern, collection, area in _SPLIT:
        if _fits(pattern, segments):
            if collection == "run_results" and segments[-1] in RUN_AUX_FILES:
                collection = "run_docs"
            project = segments[1] if segments[0] == "projects" and len(segments) > 1 else ""
            return Route(collection, area, key.endswith(".jsonl"), project)
    raise AssertionError("the last rule matches every key")  # pragma: no cover


def area_of(key: str) -> str:
    """The store area (`AREAS`) of a key; a directory key gets the area of its first rule."""
    return route(key).area


def _could_match(pattern: tuple[str, ...], directory: list[str]) -> bool:
    for index, segment in enumerate(directory):
        if index >= len(pattern):
            return False
        if pattern[index] == "**":
            return True
        if not fnmatchcase(segment, pattern[index]):
            return False
    return len(pattern) > len(directory)


def under(directory: str) -> list[tuple[str, str]]:
    """`(collection, area)` of every rule that may match a key strictly below `directory`.
    A superset (first-match shadowing is ignored), so a listing never misses a collection."""
    segments = [s for s in directory.split("/") if s]
    return sorted({(c, a) for p, c, a in _SPLIT if _could_match(p, segments)})


def repo_redactor(extra: dict[str, str] | None = None) -> Redactor:
    """A `Redactor` over every non-empty repo `.env` value, every stored credential (U11, M8), every
    stored browser session value (U12, M40), the live Mongo URI and `extra`."""
    path = repo_root() / ".env"
    values = {k: v for k, v in read_dotenv(path).items() if k and v} if path.is_file() else {}
    uri = mongo_uri()
    from autotester.browser.profiles import stored_session_values  # lazy: it imports core.env

    return Redactor({**redaction_values(values), **stored_session_values(),
                     **({MONGO_URI_ENV: uri} if uri else {}), **(extra or {})})


def text_sha(text: str) -> str:
    """The digest `put_if` compares: SHA-256 of the text as `get` returns it, UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_matches(line: str, field: str, value: str) -> bool:
    """True when the JSON row's `field` (as text) equals `value`; a missing field reads `None`."""
    try:
        row = json.loads(line)
    except ValueError:
        return False
    return isinstance(row, dict) and str(row.get(field)) == value


def within(key: str, prefix: str) -> bool:
    """`key` is `prefix` itself or sits below it, on a `/` boundary (`projects/a` is not `ab`)."""
    base = prefix.rstrip("/")
    return key == base or key.startswith(base + "/")


def require_scope(prefix: str) -> str:
    """The prefix `delete_prefix` may act on: never empty, so it can never mean 'everything'."""
    if not prefix.strip("/"):
        raise UnsafeName("delete_prefix needs a non-empty prefix, never the whole store")
    return prefix


def child_names(keys: Iterable[str], directory: str, suffix: str = "") -> list[str]:
    """Sorted names directly below `directory` (a file or a sub-directory), from file keys."""
    base = directory.rstrip("/") + "/" if directory.strip("/") else ""
    names = {k[len(base):].split("/", 1)[0] for k in keys if k.startswith(base)}
    return sorted(n for n in names if n and n.endswith(suffix))


def store_selection() -> dict[str, str]:
    """Area -> backend from `AUTOTESTER_STORE` (default file) + `AUTOTESTER_STORE_AREAS=a=b,..`."""
    chosen = dict.fromkeys(AREAS, os.environ.get("AUTOTESTER_STORE", "").strip() or "file")
    for item in filter(None, (i.strip() for i in os.environ.get("AUTOTESTER_STORE_AREAS", "")
                              .split(","))):
        area, _, backend = (piece.strip() for piece in item.partition("="))
        if area not in AREAS:
            raise StoreSelectionError(f"AUTOTESTER_STORE_AREAS: unknown area {area!r} in {item!r}")
        if area in UNROUTED and backend not in ("", "file"):
            raise StoreSelectionError(f"AUTOTESTER_STORE_AREAS: area {area!r} routes nothing yet; "
                                      f"{UNROUTED[area]} owns it, so leave it on file")
        chosen[area] = backend
    for name in chosen.values():
        if name not in BACKENDS:
            raise StoreSelectionError(f"unknown store backend {name!r}; use one of {BACKENDS}")
    return chosen


def ping_backends(selection: dict[str, str],
                  open_backend: Callable[[str], StateBackend]) -> dict[str, str]:
    """Open and ping each backend the selection chose, once (M27). A failure is re-raised with
    fixed text, the exception class name and the areas on that backend; the source message is
    never relayed (M9), so a raiser that quotes a URI cannot leak it through here."""
    for name in sorted(set(selection.values())):
        try:
            open_backend(name).ping()
        except StoreDown as exc:
            areas = ", ".join(a for a, n in selection.items() if n == name)
            raise type(exc)(f"state store unreachable ({type(exc).__name__}); "
                           f"areas on {name}: {areas}") from None
    return selection


def split_graph(text: str) -> tuple[str, list[str], list[str]] | None:
    """`(skeleton, node texts, edge texts)` when `text` is a persona whose graph can be split (M22),
    else `None`. The skeleton is the persona with an empty node and edge list."""
    try:
        obj = json.loads(text)
    except ValueError:
        return None
    graph = obj.get("graph") if isinstance(obj, dict) else None
    if not (isinstance(graph, dict) and isinstance(graph.get("nodes"), list)
            and isinstance(graph.get("edges"), list)):
        return None

    def dump(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    skeleton = {**obj, "graph": {**graph, "nodes": [], "edges": []}}
    return dump(skeleton), [dump(n) for n in graph["nodes"]], [dump(e) for e in graph["edges"]]


def join_graph(skeleton: str, nodes: list[str], edges: list[str]) -> str:
    """The persona text re-assembled from `split_graph` parts (equal as a model, not byte-equal)."""
    obj = json.loads(skeleton)
    obj["graph"]["nodes"] = [json.loads(n) for n in nodes]
    obj["graph"]["edges"] = [json.loads(e) for e in edges]
    return json.dumps(obj, ensure_ascii=False)
