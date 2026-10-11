"""Shared harness for the dispatch-hardening probes. Fake canary only; temp data root."""
from __future__ import annotations
import base64, binascii, json, os, re, sys, tempfile, urllib.parse
os.environ["AUTOTESTER_APPROVAL_KEY"] = "test-only-signing-key-never-a-real-secret"
from pathlib import Path
from typing import Any

ROOT = Path("C:/Users/Lenovo/AppData/Local/Temp/chkA_t179r1_355800")
HEAD = ROOT / "head"
sys.path.insert(0, str(HEAD / "tests"))
import autotester  # noqa
assert str(HEAD) in str(Path(autotester.__file__).resolve()), autotester.__file__

from autotester.agents import tools, guards  # noqa
from autotester.agents.context import AgentContext  # noqa
from autotester.browser.secrets import SecretStore  # noqa
from autotester.providers.mock import MockProvider  # noqa
from autotester.schema.agent_layer import AgentToolName, RefusalClass, ToolOutcome  # noqa
from autotester.schema.enums import Action, ApprovalKind, Outcome, WritePolicy, Result  # noqa
from autotester.schema.flowspec import Step  # noqa
from autotester.schema.run import RawResult  # noqa
from autotester.schema.verdict import Criterion, Rubric  # noqa
from autotester.store.project_store import ProjectStore  # noqa
from test_agent_tools import _project, _case, _grant, _nav, BASE  # noqa

CANARY = "CANARY-pw-7f3a9c"
KNOWN = {n.value for n in AgentToolName} | {"unknown"}
ZW = "\u200b\u200c\u200d\ufeff\u00ad"


REAL_GRADE = tools.grade.grade


class Spy:
    def __init__(self):
        self.calls: dict[str, int] = {}
        self.sessions = 0
    def hit(self, n):
        self.calls[n] = self.calls.get(n, 0) + 1
    def total(self):
        return sum(self.calls.values()) + self.sessions


class _Session:
    def __enter__(self): return self
    def __exit__(self, *e): return None


def make_ctx(data_root: Path, spy: Spy, policy=WritePolicy.ALLOW_WRITES, judge=None):
    project = _project(policy)
    store = ProjectStore("demo", data_root)
    store.paths.ensure()
    store.save_project(project)
    def open_session(observer):
        spy.sessions += 1
        return _Session()
    ctx = AgentContext(project=project, store=store, secrets=SecretStore(project, {"APP_PASS": CANARY}),
                       judge=judge or MockProvider(), run_id="run-1", open_session=open_session)
    _grant(store, ApprovalKind.LIVE_CASE)
    _grant(store, ApprovalKind.CRAWL)
    return ctx


def add_case(ctx, rubric=False, result=False):
    case = ctx.store.add_case(_case([_nav()], rubric=rubric))
    if rubric:
        ctx.store.save_rubric(Rubric(id="r1", case_id=case.id, criteria=[Criterion(id="c1", text="t")]))
    if result:
        ctx.store.save_result("run-1", RawResult(case_id=case.id, outcome=Outcome.COMPLETED))
    return case


def patch_stages(spy: Spy, result_factory=None):
    """Install spies on tools.execute.run_case/explore.run_crawl/grade.grade/catalog.catalog; returns restore()."""
    from autotester.schema.crawl import Crawl
    from autotester.schema.catalog import Catalog
    from autotester.schema.verdict import Verdict
    saved = (tools.execute.run_case, tools.explore.run_crawl, tools.grade.grade, tools.catalog.catalog)
    def rc(case, session):
        spy.hit("run_case")
        return result_factory(case) if result_factory else RawResult(case_id=case.id, outcome=Outcome.COMPLETED)
    tools.execute.run_case = rc
    tools.explore.run_crawl = lambda *a, **k: (spy.hit("run_crawl"), Crawl(project="demo"))[1]
    tools.grade.grade = lambda rub, res, run_id, *a, **k: (spy.hit("grade"), Verdict(run_id=run_id, case_id=res.case_id, rubric_hash="h", result=Result.PASS, grader_provider="mock"))[1]
    tools.catalog.catalog = lambda *a, **k: (spy.hit("catalog"), Catalog(project="demo"))[1]
    def restore():
        tools.execute.run_case, tools.explore.run_crawl, tools.grade.grade, tools.catalog.catalog = saved
    return restore


# ---- canary variants -------------------------------------------------------------------------
def b64_variants(s: str) -> list[str]:
    raw = s.encode()
    out = []
    for urlsafe in (False, True):
        for k in range(3):
            enc = (base64.urlsafe_b64encode if urlsafe else base64.b64encode)(b"x" * k + raw).decode().rstrip("=")
            start = -(-8 * k // 6)  # ceil
            end = (8 * (k + len(raw))) // 6
            out.append(enc[start:end])
    return out


def variants(s: str = CANARY) -> dict[str, str]:
    v = {"raw": s, "lower": s.lower(), "upper": s.upper(), "reversed": s[::-1],
         "hex_lower": s.encode().hex(), "hex_upper": s.encode().hex().upper(),
         "pct_all": "".join(f"%{b:02x}" for b in s.encode()),
         "pct_all_upper": "".join(f"%{b:02X}" for b in s.encode()),
         "pct_quote": urllib.parse.quote(s, safe=""),
         "spaced": " ".join(s), "zw_split": "\u200b".join(s), "dash_split": "-".join(s),
         "rev_hex": s[::-1].encode().hex(),
         "b32": base64.b32encode(s.encode()).decode().rstrip("=")}
    for i, b in enumerate(b64_variants(s)):
        v[f"b64_{'url' if i >= 3 else 'std'}_off{i % 3}"] = b
    v["b64_rev"] = base64.b64encode(s[::-1].encode()).decode().rstrip("=")
    return v


def _norm(text: str) -> str:
    BS = chr(92)
    text = re.sub(BS + BS + "u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    for esc in ("n", "t", "r"):
        text = text.replace(BS + esc, "")
    return re.sub("[\s​-‍﻿­ ]", "", text)


def hits_in_text(text: str, vs: dict[str, str] | None = None) -> list[str]:
    vs = vs or variants()
    n = _norm(text)
    found = []
    for name, val in vs.items():
        if name in ("spaced", "zw_split"):
            continue  # whitespace-stripped normalisation handles these via 'raw' on the normalised text
        if val in text or val in n:
            found.append(name)
    for name in ("spaced", "zw_split", "dash_split"):
        if vs[name] in text:
            found.append(name)
    # normalised-raw catches spaced/zw/split-by-whitespace
    if CANARY in n and "raw" not in found:
        found.append("raw_after_normalise")
    if CANARY[::-1] in n and "reversed" not in found:
        found.append("reversed_after_normalise")
    return found


def hits_in_tree(root: Path) -> list[tuple[str, list[str]]]:
    out = []
    vs = variants()
    for p in root.rglob("*"):
        if p.is_file():
            data = p.read_bytes()
            text = data.decode("utf-8", "ignore")
            h = hits_in_text(text, vs)
            # also raw-bytes grep for utf-16 content
            if h:
                out.append((str(p.relative_to(root)), h))
    return out


def tree_files(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def longest_partial(text: str, minlen: int = 6):
    best = (0, "")
    for name, v in variants().items():
        if name in ("spaced", "zw_split", "dash_split", "lower", "upper"):
            continue
        for L in range(len(v), max(minlen - 1, best[0]), -1):
            if any(v[i:i + L] in text for i in range(0, len(v) - L + 1)):
                best = (L, name)
                break
    return best
