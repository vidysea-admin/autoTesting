"""Shared helpers for the T-178 C5 probes (throwaway roots only; fake secret)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

S = 'Pa$$w0rd"<b>&\'\\ü-ZZ9'          # planted fake secret, quotes/angle/amp/backslash/unicode
S_NOBS = 'Pa$$w0rd"<b>&\'ü-ZZ9'        # same without backslash (a bundle-name-legal variant)
BASE = Path(__file__).resolve().parent
ROOTS = BASE / "roots"


def mk_root(name: str, secret: str = S) -> Path:
    root = ROOTS / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    # .env value is single-quoted-free: parse_env treats a leading quote specially, ours starts with P
    (root / ".env").write_text(f"ZZ_PROBE_PW={secret}\n", encoding="utf-8")
    os.environ["AUTOTESTER_ROOT"] = str(root)
    return root


def seed(root: Path, flow_name: str, *, approved: bool = True, slug: str = "demo"):
    from autotester.schema.enums import Action, ReviewStatus
    from autotester.schema.flowspec import Flow, FlowSpec, Review, Step
    from autotester.schema.project import Project
    from autotester.store.project_store import ProjectStore

    store = ProjectStore(slug, root)
    store.save_project(Project(slug=slug, name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"]))
    flow = Flow(id="flow-login", name=flow_name, entry_screen="scr_signin",
                preconditions=[f"user knows {S}"],
                steps=[Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
                       Step(order=2, action=Action.FILL, target=f"Password {S}", value=S,
                            note=f"typed {S}"),
                       Step(order=3, action=Action.FILL, target="Pwd", value="{{SECRET:ZZ_PROBE_PW}}"),
                       Step(order=4, action=Action.CLICK, target="Sign in")])
    status = ReviewStatus.APPROVED if approved else ReviewStatus.DRAFT
    store.save_flowspec(FlowSpec(project=slug, review=Review(status=status, by="h", at="t"),
                                 flows=[flow]))
    return store


def raw_in(path: Path, needle: str = S) -> str:
    """RAW / ESC(json-escaped) / SCRUBBED-or-absent for one file."""
    if not path.exists():
        return "NOFILE"
    t = path.read_text(encoding="utf-8")
    import json
    if needle in t:
        return "RAW"
    if json.dumps(needle, ensure_ascii=False)[1:-1] in t:
        return "RAW-AS-JSON-ESCAPED"   # still the secret (recoverable by json.loads)
    if json.dumps(needle)[1:-1] in t:
        return "RAW-AS-JSON-ESCAPED(ascii)"
    return "CLEAN"
