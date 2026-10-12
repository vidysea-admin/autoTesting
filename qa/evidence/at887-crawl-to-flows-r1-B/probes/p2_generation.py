"""Probe 2 (checker B, AT-887 r1): case generation on a crawl-merged spec, provider spied.
Synthetic crawl, tmp root, MockProvider spy only (no model call). Run with python -I."""
from __future__ import annotations

import base64
import binascii
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

os.environ.setdefault("AUTOTESTER_ALLOWED_HOSTS", "testserver")
os.environ.setdefault("AUTOTESTER_APPROVAL_KEY", "probe-only-key")
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from autotester.cli_crawl import _merge_into_flowspec
from autotester.core.paths import RepoDocs
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.crawl import Crawl
from autotester.schema.enums import Action
from autotester.schema.project import Project, SecretRef
from autotester.schema.screen_graph import ScreenEdge, ScreenNode
from autotester.stages.expand import expand, propose_cases
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore
from autotester.ui import routes_learn
from autotester.ui.app import app

SECRET = "Hunter2-Zebra-4411"
UNDECL = "Other-Projects-Key-9082"
PROJ = Project(slug="demo", name="Demo", base_url="https://demo.test", allowed_domains=["demo.test"],
               secrets=[SecretRef(key="ST_PASS", domains=["demo.test"])])

CHAIN = [  # (name, path, edge target)  -- every edge target ENDS with the sensitive token
    ("Help", "/help", "text=Helpline +91 98765 43210"),
    ("Mail", "/mail", "text=Mail ada.lovelace@example.org"),
    ("Fax", "/fax", "text=Fax 415-555-2671"),
    ("Office", "/office", "text=Office +44 20 7946 0958"),
    ("Mobile", "/mobile", "text=Mobile 9876543210"),
    ("Paren", "/paren", "text=Call (415) 555-2671"),
    ("Token", "/token", f"text=Token {SECRET}"),
    ("Other", "/other", f"text=Other {UNDECL}"),
    ("Last", "/last", 'role=link[name="Finish"] >> nth=0'),
]


def make(root: Path, extra_target: str | None = None):
    store = ProjectStore("demo", root)
    store.save_project(PROJ)
    (root / ".env").write_text(f"ST_PASS={SECRET}\nOTHER_KEY={UNDECL}\n", encoding="utf-8")
    cid = "crawl_p2"
    store.save_crawl(Crawl(project="demo", id=cid, login_case_id="case_login"))
    prev = ScreenNode(crawl_id=cid, project="demo", url_template="demo.test/home",
                      url_example="https://demo.test/home?email=ada.lovelace@example.org",
                      signature="s_home", name="Home")
    store.add_node(prev)
    for i, (name, path, target) in enumerate(CHAIN):
        if extra_target is not None and i == 2:
            target = extra_target
        e = ScreenEdge(crawl_id=cid, from_node=prev.id, action=Action.NAVIGATE, target=target,
                       name=name, outcome="navigated")
        store.add_edge(e)
        prev = ScreenNode(crawl_id=cid, project="demo", url_template=f"demo.test{path}",
                          url_example=f"https://demo.test{path}", signature=f"s_{name}", name=name,
                          discovered_by=e.id)
        store.add_node(prev)
    _merge_into_flowspec(store, "demo", cid)
    spec = approve(store.load_flowspec(), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for row in rows:
        store.review_case_proposal(row.id, "umesh", approved=True)
    return store, spec


class Spy(MockProvider):
    def available(self) -> bool:
        return True


def spy():
    return Spy(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 400})


def step_lines(prompt: str) -> list[str]:
    return [ln for ln in prompt.splitlines() if re.match(r"^\d+\. (navigate|click) ", ln)]


EXPECTED = [
    "1. navigate https://demo.test/home?email=<email>",
    "2. click text=Helpline <phone>",
    "3. click text=Mail <email>",
    "4. click text=Fax <phone>",
    "5. click text=Office <phone>",
    "6. click text=Mobile <phone>",
    "7. click text=Call <phone>",
    f"8. click text=Token [REDACTED]:ST_PASS",
    "9. click text=Other [REDACTED]:OTHER_KEY",
    '10. click role=link[name="Finish"] >> nth=0',
]


def main():
    out = {}
    tmp = Path(tempfile.mkdtemp(prefix="r1b_p2_"))
    # --- A. masked prompt on the merged spec -------------------------------------------------
    store, spec = make(tmp / "a")
    print("flows in merged spec:", [(f.id, len(f.steps)) for f in spec.flows], "name:", spec.flows[0].name)
    s = spy()
    cases = expand(store.load_flowspec(), s, RepoDocs(), store=store)
    prompts = [p for _, p in s.prompts]
    out["provider_calls"] = len(prompts)
    leaks = [(tok, sum(tok in p for p in prompts)) for tok in
             (SECRET, UNDECL, "ada.lovelace", "98765", "7946", "555-2671", "9876543210",
              base64.b64encode(SECRET.encode()).decode())]
    out["leaks_in_prompts"] = leaks
    got = step_lines(prompts[0]) if prompts else []
    out["step_lines_p0"] = got
    out["exact_lines_match"] = got == EXPECTED
    out["all_prompts_same_lines"] = all(step_lines(p) == got for p in prompts)
    out["flow_name_line"] = [ln for ln in prompts[0].splitlines() if "crawl path" in ln][:2]
    print("provider calls", len(prompts), "exact lines match:", got == EXPECTED)
    for g, e in zip(got, EXPECTED):
        print(("  ok  " if g == e else "  DIFF"), repr(g), "" if g == e else f"expected {e!r}")
    print("leaks:", leaks)
    # --- B. planted encoded secret through the Generate route -------------------------------
    enc_variants = {
        "base64": base64.b64encode(SECRET.encode()).decode(),
        "hex": binascii.hexlify(SECRET.encode()).decode(),
        "percent-single": "%48unter%32-Zebra-4411",
        "percent-double": "%2548unter%2532-Zebra-4411",
        "reversed": SECRET[::-1],
        "upper-spaced": " ".join(SECRET.upper()),
    }
    out["encoded"] = {}
    for label, enc in enc_variants.items():
        root = tmp / f"b_{label}"
        store, spec = make(root, extra_target=f"text=Token {enc}")
        sp = spy()
        routes_learn.LangChainFallbackProvider = lambda sp=sp: sp  # the route's own constructor seam
        os.environ["AUTOTESTER_ROOT"] = str(root)
        before_cases = len(store.list_cases())
        r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
        echoed = [t for t in (SECRET, enc) if t in r.text]
        out["encoded"][label] = dict(status=r.status_code, provider_calls=len(sp.prompts),
                                     cases_before=before_cases, cases_after=len(store.list_cases()),
                                     echoed=echoed, html=r.headers.get("content-type", "NONE")[:20], body=r.text[:200],
                                     themed="AutoTester" in r.text and "Internal Server Error" not in r.text)
        print("encoded", label, out["encoded"][label])
    # --- C. an unrelated ValueError: what is the user told? ---------------------------------
    class Boom(Spy):
        def __init__(self, exc):
            super().__init__(responses={})
            self.exc = exc

        def act(self, prompt, *a, **k):
            self.prompts.append(("agent", prompt))
            raise self.exc

    try:
        class M(BaseModel):
            x: int
        M(x="not-an-int")
    except ValidationError as ve:
        vexc = ve
    out["unrelated"] = {}
    for label, exc in (("ValueError raised by provider AFTER the prompt was sent", ValueError("provider returned malformed JSON")),
                       ("pydantic ValidationError (a ValueError) on the model's reply", vexc)):
        root = tmp / f"c_{abs(hash(label))}"
        store, spec = make(root)
        sp = Boom(exc)
        routes_learn.LangChainFallbackProvider = lambda sp=sp: sp
        os.environ["AUTOTESTER_ROOT"] = str(root)
        r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
        text = re.sub(r"<[^>]+>", " ", r.text)
        m = re.search(r"Generating cases failed partway through:[^<]{0,120}", r.text)
        out["unrelated"][label] = dict(status=r.status_code, provider_calls=len(sp.prompts),
                                       user_sentence=m.group(0) if m else text[-300:])
        print("unrelated", label, out["unrelated"][label])
    # --- D. a plain provider failure still shows its own text ---------------------------------
    from autotester.providers.base import ProviderError
    root = tmp / "d"
    store, spec = make(root)
    sp = Boom(ProviderError("quota exhausted"))
    routes_learn.LangChainFallbackProvider = lambda sp=sp: sp
    os.environ["AUTOTESTER_ROOT"] = str(root)
    r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
    m = re.search(r"Generating cases failed partway through:[^<]{0,120}", r.text)
    out["provider_error"] = dict(status=r.status_code, sentence=m.group(0) if m else None)
    print("provider error", out["provider_error"])
    Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


main()
