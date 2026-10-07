from autotester.core.redact import Redactor
from autotester.schema.ai_target import ReadScope
from autotester.stages.read_context import read_context

def test_noncyclic_alias_exact_refusal(tmp_path):
    (tmp_path / "note.md").write_text("---\nx: &a [1]\ny: *a\n---\n", encoding="utf-8")
    result = read_context([tmp_path], scope=ReadScope(project="fixture", project_root=str(tmp_path)), redactor=Redactor({}))
    assert result.documents == []
    assert [r.reason for r in result.refusals] == ["yaml_alias"]
