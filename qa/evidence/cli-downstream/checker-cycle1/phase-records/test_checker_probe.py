from pathlib import Path
import pytest
from downstream_fixture import DownstreamSession,downstream_fixture
from autotester.schema.enums import ReviewStatus
from autotester.schema.flowspec import Review
from autotester.schema.run_state import StageName
from autotester.stages.review import FlowSpecNotReviewed

def test_current_authority_veto_after_frozen_expansion(tmp_path,monkeypatch):
    store,project,spec,model,generator,judge,ctx=downstream_fixture(tmp_path)
    ref=ctx.runners[StageName.EXPAND](ctx,model)
    before={p.relative_to(store.paths.run_dir(ctx.run_id)):p.read_bytes() for p in store.paths.run_dir(ctx.run_id).rglob('*') if p.is_file()}
    store.save_flowspec(spec.model_copy(update={'review':Review(status=ReviewStatus.NEEDS_EDIT)}))
    def forbidden(*args,**kwargs):
        pytest.fail('constructor reached after canonical veto')
    monkeypatch.setattr(DownstreamSession,'__init__',forbidden)
    with pytest.raises(FlowSpecNotReviewed):
        ctx.runners[StageName.EXECUTE](ctx,ref)
    assert not store.load_results(ctx.run_id) and not store.load_verdicts(ctx.run_id)
    assert {p.relative_to(store.paths.run_dir(ctx.run_id)):p.read_bytes() for p in store.paths.run_dir(ctx.run_id).rglob('*') if p.is_file()}==before
