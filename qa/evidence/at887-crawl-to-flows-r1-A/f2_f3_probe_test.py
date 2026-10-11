"""Checker probe (throwaway copy only): F2 route behaviour and F3 prompt lines."""
from __future__ import annotations

import base64
import hashlib
import os

import pytest
from fastapi.testclient import TestClient

from autotester.core.paths import RepoDocs
from autotester.providers.base import ProviderError
from autotester.providers.mock import MockProvider
from autotester.schema.case import ExpandedSteps
from autotester.schema.enums import Action, CaseClass
from autotester.schema.flowspec import Flow, FlowSpec, Step
from autotester.schema.project import Project, SecretRef
from autotester.stages.expand import build_expand_prompt, propose_cases
from autotester.stages.review import approve
from autotester.store.project_store import ProjectStore
from autotester.ui.app import app

SECRET = "Hunter2-Zebra-4411"


def _tree(root):
    out = {}
    for dp, _dn, fns in os.walk(root):
        for f in fns:
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root)] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    return out


def _setup(tmp_path, monkeypatch, flows):
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    (tmp_path / ".env").write_text(f"ST_PASS={SECRET}\n", encoding="utf-8")
    store = ProjectStore("demo", tmp_path)
    store.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                               allowed_domains=["demo.test"],
                               secrets=[SecretRef(key="ST_PASS", domains=["demo.test"])]))
    spec = approve(FlowSpec(project="demo", flows=flows), by="umesh")
    store.save_flowspec(spec)
    rows = propose_cases(spec)
    store.stage_case_proposals(rows)
    for row in rows:
        store.review_case_proposal(row.id, "umesh", approved=True)
    return store


def _flow(fid, value):
    return Flow(id=fid, name="Sign in " + fid, entry_screen="scr", steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://demo.test/signin"),
        Step(order=2, action=Action.FILL, target="password", value=value)])


def _spy(monkeypatch):
    class Spy(MockProvider):
        def available(self):
            return True
    spy = Spy(responses={"agent": [ExpandedSteps(steps=[], rationale="n/a")] * 200})
    import autotester.ui.routes_learn as m
    monkeypatch.setattr(m, "LangChainFallbackProvider", lambda: spy)
    return spy


def test_f2_unrelated_valueerror_is_labelled_refused_unsent(tmp_path, monkeypatch):
    store = _setup(tmp_path, monkeypatch, [_flow("flow_a", "x")])
    _spy(monkeypatch)
    import autotester.ui.routes_learn as m

    def boom(*a, **k):
        raise ValueError("programming error: index out of range in my code")
    monkeypatch.setattr(m, "expand", boom)
    r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
    print("UNRELATED-VALUEERROR status", r.status_code, "|", "refused unsent" in r.text,
          "| echoes real text:", "programming error" in r.text)


def test_f2_provider_error_text_unchanged(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, [_flow("flow_a", "x")])
    _spy(monkeypatch)
    import autotester.ui.routes_learn as m

    def boom(*a, **k):
        raise ProviderError("quota exceeded for key")
    monkeypatch.setattr(m, "expand", boom)
    r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
    print("PROVIDERERROR status", r.status_code, "| text kept:", "quota exceeded" in r.text)


def test_f2_guard_refusal_second_flow_writes_nothing(tmp_path, monkeypatch):
    enc = base64.b64encode(SECRET.encode()).decode()
    store = _setup(tmp_path, monkeypatch, [_flow("flow_a", "x"), _flow("flow_b", enc)])
    spy = _spy(monkeypatch)
    before = _tree(tmp_path)
    r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
    after = _tree(tmp_path)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    print("MULTIFLOW status", r.status_code, "prompts sent before refusal:", len(spy.prompts),
          "cases:", len(store.list_cases()), "files changed by POST:", changed)
    leaked = [p for p in spy.prompts if SECRET in p or enc in p]
    print("MULTIFLOW secret/encoded in any sent prompt:", len(leaked), "| in page:",
          SECRET in r.text or enc in r.text)
    assert r.status_code == 400 and not leaked and store.list_cases() == []


def test_f2_guard_refusal_first_flow_nothing_changed_on_disk(tmp_path, monkeypatch):
    enc = base64.b64encode(SECRET.encode()).decode()
    _setup(tmp_path, monkeypatch, [_flow("flow_b", enc)])
    spy = _spy(monkeypatch)
    before = _tree(tmp_path)
    r = TestClient(app).post("/projects/demo/cases/generate", follow_redirects=False)
    after = _tree(tmp_path)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    print("SINGLE status", r.status_code, "prompts", len(spy.prompts), "files changed:", changed)
    print("SINGLE page body snippet:", r.text[r.text.find("partway") - 10: r.text.find("partway") + 90])


def _lines(flow, cls=CaseClass.SERVER_ERROR):
    p = build_expand_prompt(flow, cls, RepoDocs())
    return p


@pytest.mark.parametrize("val", ["+91 98765 43210", "98765 43210", "9876543210",
                                 "(022) 2345 6789", "ada@example.org", "ada.lovelace+x@sub.example.org"])
def test_f3_every_step_masked_and_ordinals_intact(val):
    flow = Flow(id="f", name="Call " + val, entry_screen="s", steps=[
        Step(order=1, action=Action.NAVIGATE, target="https://app.test/x"),
        Step(order=2, action=Action.FILL, target="contact", value=val),
        Step(order=3, action=Action.CLICK, target="Continue"),
        Step(order=4, action=Action.FILL, target="note " + val, value="see " + val),
        Step(order=5, action=Action.CLICK, target="Done")])
    p = _lines(flow)
    start = p.find("1. navigate")
    steps = p[start:].split("\n")[:5]
    print("F3", repr(val), "->", [s for s in steps])
    assert [s.split(".")[0] for s in steps] == ["1", "2", "3", "4", "5"]
    assert val not in p


def test_f3_forms_not_masked_informational():
    outs = {}
    for v in ["ada%40example.org", "ada [at] example.org", "ADA@EXAMPLE.ORG", "mailto:a@b.co",
              "+919876543210", "91-98765-43210", "tel:+91 98765 43210"]:
        flow = Flow(id="f", name="n", entry_screen="s", steps=[
            Step(order=1, action=Action.FILL, target="t", value=v),
            Step(order=2, action=Action.CLICK, target="Go")])
        p = _lines(flow)
        line = p[p.find("1. fill"):].split("\n")[0]
        outs[v] = line
    for k, v in outs.items():
        print("F3-FORM", repr(k), "->", repr(v))


def test_f3_placeholder_and_name():
    flow = Flow(id="f", name="Phone +91 98765 43210 / ada@x.org", entry_screen="s", steps=[
        Step(order=1, action=Action.FILL, target="password", value="{{SECRET:ST_PASS}}"),
        Step(order=2, action=Action.CLICK, target="Go")])
    p = _lines(flow)
    print("F3-PLACEHOLDER", "{{SECRET:ST_PASS}}" in p, "| name masked:",
          "98765" not in p and "ada@x.org" not in p)
    i = p.find("crawl")
    for ln in p.split("\n"):
        if "Phone" in ln or "<phone>" in ln:
            print("F3-NAMELINE", repr(ln))
