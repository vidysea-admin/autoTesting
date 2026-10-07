"""Synthetic filesystem exception boundary probe, diagnostic only."""
import base64
import traceback
from pathlib import Path

import pytest

from autotester.core.redact import Redactor
from autotester.schema.ai_target import ReadScope
from autotester.stages.discover import scan
from autotester.stages.read_context import read_context

@pytest.mark.parametrize("encoded", [False, True])
@pytest.mark.parametrize("operation", ["missing", "scan_open", "context_open"])
def test_filesystem_error_cannot_disclose_secret(tmp_path, monkeypatch, encoded, operation):
    secret = "filesystem-probe-secret"
    token = base64.b64encode(secret.encode()).decode() if encoded else secret
    scope = ReadScope(project="fixture", project_root=str(tmp_path))
    redactor = Redactor({"SYNTHETIC": secret})
    if operation != "missing":
        (tmp_path / "note.md").write_text("title\n", encoding="utf-8")
        def denied(*args, **kwargs):
            raise PermissionError(f"cannot open {token}")
        monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(OSError) as caught:
        if operation == "context_open":
            read_context([tmp_path], scope=scope, redactor=redactor)
        else:
            scan(tmp_path / token if operation == "missing" else tmp_path, [],
                 scope=scope, redactor=redactor)
    diagnostic = "".join(traceback.format_exception(caught.value))
    assert redactor.is_clean(diagnostic) and not redactor.contains_folded(diagnostic), (
        "filesystem exception string/traceback exposes recoverable synthetic secret")
