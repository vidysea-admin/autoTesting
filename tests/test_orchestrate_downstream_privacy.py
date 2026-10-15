"""Adapter-owned persistence rejects adversarial outputs before the first unsafe write."""

from pathlib import Path

import pytest
from downstream_fixture import downstream_fixture

from autotester.browser.secrets import SecretStore
from autotester.schema.case import Case
from autotester.schema.enums import CaseClass, CaseKind, Outcome
from autotester.schema.run import RawResult
from autotester.schema.run_state import StageName
from autotester.stages import orchestrate_downstream as stages
from autotester.stages import orchestrate_execute as execution
from autotester.stages.script_replay import ScriptedRun


def test_downstream_rejects_secret_outputs_before_case_or_raw_persistence(tmp_path, monkeypatch):
    store, project, spec, model, _, _, ctx = downstream_fixture(tmp_path)
    canary = "downstream-adversarial-canary-987654"
    store.paths.env_file.write_text(f"CANARY={canary}\n", encoding="utf-8")
    ctx.secrets = SecretStore.load(project, store.paths.env_file, strict=False)
    safe = Case(project=project.slug, flow_id=spec.flows[0].id, kind=CaseKind.BEST,
                case_class=CaseClass.HAPPY, title="Safe case", steps=spec.flows[0].steps)
    unsafe = safe.model_copy(update={"id": "case-unsafe", "rationale": canary})
    original = stages.expand
    monkeypatch.setattr(stages, "expand", lambda *_a, **_k: [safe, unsafe])
    with pytest.raises(ValueError, match="raw secret"):
        ctx.runners[StageName.EXPAND](ctx, model)
    assert store.list_cases() == []  # entire set was checked before the first store write
    monkeypatch.setattr(stages, "expand", original)
    expanded = ctx.runners[StageName.EXPAND](ctx, model)
    case_id = store.list_cases()[0].id
    raw = RawResult(case_id=case_id, outcome=Outcome.ERRORED, error=canary)
    monkeypatch.setattr(execution, "observe_case", lambda *_: (ScriptedRun(raw, "record"), None))
    with pytest.raises(ValueError, match="raw secret"):
        ctx.runners[StageName.EXECUTE](ctx, expanded)
    assert store.load_results(ctx.run_id) == store.load_verdicts(ctx.run_id) == []
    for path in Path(store.paths.dir).rglob("*"):
        if path.is_file() and path != store.paths.env_file:
            assert canary.encode() not in path.read_bytes()
