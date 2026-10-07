"""Independent post-repair oracles for sanitized filesystem and refusal boundaries."""
import base64
import traceback
from pathlib import Path

import pytest

from autotester.core.consent import ApprovalRequired
from autotester.core.redact import Redactor
from autotester.schema.ai_target import ReadScope
from autotester.stages.discover import scan
from autotester.stages.read_context import read_context

SECRET = "checker-repair-secret-longvalue"
TOKEN = base64.b64encode(SECRET.encode()).decode()

@pytest.mark.parametrize("operation", ["missing", "scan_open", "context_open"])
@pytest.mark.parametrize("token", [SECRET, TOKEN])
def test_filesystem_subclass_and_diagnostics(tmp_path, monkeypatch, operation, token):
    scope = ReadScope(project="fixture", project_root=str(tmp_path))
    guard = Redactor({"SYNTHETIC": SECRET})
    if operation == "missing":
        expected = FileNotFoundError
        call = lambda: scan(tmp_path / token, [], scope=scope, redactor=guard)
    else:
        (tmp_path / "note.md").write_text("---\ntitle: benign\n---\n", encoding="utf-8")
        def deny(*args, **kwargs):
            raise PermissionError(13, "denied " + token, str(tmp_path / token))
        monkeypatch.setattr(Path, "open", deny)
        expected = PermissionError
        call = (lambda: read_context([tmp_path], scope=scope, redactor=guard)) if operation == "context_open" else (lambda: scan(tmp_path, [], scope=scope, redactor=guard))
    with pytest.raises(expected) as caught:
        call()
    assert type(caught.value) is expected
    assert str(caught.value) == "filesystem access refused"
    assert caught.value.__suppress_context__
    diagnostic = "".join(traceback.format_exception(caught.value))
    guard.assert_clean(diagnostic)
    assert caught.value.filename is None

def test_secret_refusal_paths_are_guarded(tmp_path):
    (tmp_path / (TOKEN + ".py")).write_bytes(b"\x00binary")
    with pytest.raises(ValueError, match="secret"):
        scan(tmp_path, [], scope=ReadScope(project="fixture", project_root=str(tmp_path)), redactor=Redactor({"SYNTHETIC": SECRET}))

def test_dirty_project_rejected_before_filesystem(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dirty identity reached filesystem resolution")
    monkeypatch.setattr(Path, "resolve", forbidden)
    with pytest.raises(ValueError, match="secret"):
        read_context([tmp_path], scope=ReadScope(project=TOKEN, project_root=str(tmp_path)), redactor=Redactor({"SYNTHETIC": SECRET}))

def test_denial_class_and_formatted_chain_are_safe(tmp_path):
    project, outside = tmp_path / "project", tmp_path / TOKEN
    project.mkdir()
    outside.mkdir()
    with pytest.raises(ApprovalRequired) as caught:
        read_context([outside], scope=ReadScope(project="fixture", project_root=str(project)), redactor=Redactor({"SYNTHETIC": SECRET}))
    assert str(caught.value) == "refusing to start a read run: approval required"
    assert caught.value.__suppress_context__
    Redactor({"SYNTHETIC": SECRET}).assert_clean("".join(traceback.format_exception(caught.value)))

def test_clean_identity_and_provenance_unchanged(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("---\ntitle: benign\n---\n#tag\n", encoding="utf-8")
    result = read_context([tmp_path], scope=ReadScope(project="fixture", project_root=str(tmp_path)), redactor=Redactor({"SYNTHETIC": SECRET}))
    assert result.complete and len(result.documents) == 1
    assert result.documents[0].source.project == "fixture"
    assert result.documents[0].source.path == "note.md"
    assert result.documents[0].evidence_path == str(note)
    assert result.documents[0].source.text is None
