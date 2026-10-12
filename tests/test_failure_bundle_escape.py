"""AT-928: a secret with a control/quote character must not survive in trace.jsonl's JSON form."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_failure_bundle import RUN, _fixture

from autotester.core.redact import Redactor

_SECRETS = ["ab\ncd1234", "ab\tcd1234", 'ab"cd1234', "ab\cd1234", "p&ss<w>o'rdQ9", "ab\r\ncd1234"]


@pytest.mark.parametrize("secret", _SECRETS)
def test_trace_jsonl_has_no_secret_in_any_serialised_form(tmp_path: Path, secret: str) -> None:
    case, result, verdict, spans = _fixture(tmp_path)
    span = spans[0].model_copy(update={"error": f"fill {secret} failed"})
    import autotester.stages.failure_bundle as fb
    bundle = fb.build_failure_bundle(
        out_dir=tmp_path / "b", run_id=RUN, case=case, result=result, verdict=verdict,
        sources=fb.sources_from_result(RUN, tmp_path, result), spans=[span],
        redactor=Redactor({"K": secret}), failing_step=3)
    text = (bundle / "trace.jsonl").read_text(encoding="utf-8")
    import json
    assert secret not in text
    assert json.dumps(secret)[1:-1] not in text
    assert "[REDACTED]" in text
