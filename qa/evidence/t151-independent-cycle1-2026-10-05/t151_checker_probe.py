"""Credential-free independent boundary oracles; no browser or external I/O."""
import base64
from pathlib import Path

import pytest

from autotester.core.redact import Redactor
from autotester.schema.ai_target import ReadScope
from autotester.stages.discover import scan
from autotester.stages.read_context import read_context

SECRET = "checker-secret-longvalue"
ENCODED = base64.b64encode(SECRET.encode()).decode()

def test_encoded_context_output_is_guarded(tmp_path):
    (tmp_path / "note.md").write_text(f"---\ntitle: {ENCODED}\n---\n", encoding="utf-8")
    redactor = Redactor({"SYNTHETIC": SECRET})
    scope = ReadScope(project="fixture", project_root=str(tmp_path))
    try:
        receipt = read_context([tmp_path], scope=scope, redactor=redactor)
    except ValueError as error:
        assert "secret" in str(error)
    else:
        assert not redactor.contains_folded(receipt.model_dump_json()), "encoded secret survived context artifact"

def test_encoded_evidence_path_is_guarded(tmp_path):
    (tmp_path / (ENCODED + ".py")).write_text("import openai\n", encoding="utf-8")
    redactor = Redactor({"SYNTHETIC": SECRET})
    scope = ReadScope(project="fixture", project_root=str(tmp_path))
    try:
        receipt = scan(tmp_path, [], scope=scope, redactor=redactor)
    except ValueError as error:
        assert "secret" in str(error)
    else:
        assert not redactor.contains_folded(receipt.model_dump_json()), "encoded secret survived discovery artifact"

def test_unapproved_secret_path_error_is_scrubbed(tmp_path):
    project, outside = tmp_path / "project", tmp_path / SECRET
    project.mkdir()
    outside.mkdir()
    scope = ReadScope(project="fixture", project_root=str(project))
    with pytest.raises(Exception) as caught:
        scan(project, [outside], scope=scope, redactor=Redactor({"SYNTHETIC": SECRET}))
    assert SECRET not in str(caught.value), "unapproved-root error exposes raw synthetic secret"

def test_source_project_identity_is_scrubbed(tmp_path):
    (tmp_path / "note.md").write_text("---\ntitle: ordinary\n---\n", encoding="utf-8")
    redactor = Redactor({"SYNTHETIC": SECRET})
    scope = ReadScope(project=SECRET, project_root=str(tmp_path))
    try:
        receipt = read_context([tmp_path], scope=scope, redactor=redactor)
    except ValueError as error:
        assert "secret" in str(error)
    else:
        assert SECRET not in receipt.model_dump_json(), "raw secret survives Source.project"
