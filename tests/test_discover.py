"""Independent local oracles for discovery provenance and Markdown-only context."""

import base64
import contextlib
from pathlib import Path

import pytest

from autotester.core.consent import ApprovalRequired
from autotester.core.redact import Redactor
from autotester.providers.base import ProviderError
from autotester.providers.mock import MockProvider
from autotester.schema.ai_target import ReadScope, ScanLimits, Signal
from autotester.stages.discover import classify_target, scan
from autotester.stages.read_context import read_context


def _scope(root: Path, **limits: object) -> ReadScope:
    return ReadScope(project="fixture", project_root=str(root), limits=ScanLimits(**limits))

def test_signals_match_real_lines_without_importing_target(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    target = nested / "app.py"
    target.write_text("import openai\nfrom langgraph.graph import StateGraph\n"
        "raise RuntimeError('must never execute')\n", encoding="utf-8")
    result = scan(tmp_path, [nested, tmp_path], scope=_scope(tmp_path), redactor=Redactor({}))
    assert result.complete
    assert {(s.kind.value, s.line) for s in result.signals} == {("sdk", 1), ("agent_framework", 2)}
    assert all(Path(s.evidence_path) == target for s in result.signals)
    assert len(result.signals) == 2, "overlapping roots cannot duplicate evidence"

def test_context_is_metadata_only_and_secrets_are_scrubbed(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("---\ntitle: secret-fixture\ntags: [rag]\n---\n"
        "[[hidden]]\n```dataview\nTABLE private\n```\n#safe\n", encoding="utf-8")
    result = read_context([tmp_path], scope=_scope(tmp_path),
                          redactor=Redactor({"TEST": "secret-fixture"}))
    assert result.complete and len(result.documents) == 1
    doc = result.documents[0]
    assert doc.frontmatter == {"title": "[REDACTED]:TEST", "tags": ["rag"]}
    assert doc.tags == ["rag", "safe"]
    serialized = result.model_dump_json()
    assert "secret-fixture" not in serialized and "hidden" not in serialized
    assert "TABLE private" not in serialized and doc.source.text is None
    assert doc.source.path == "note.md"
@pytest.mark.parametrize("header", ["x: !!python/object:x {}", "x: &a [*a]",
    "x: [[[[[[1]]]]]]", "x: &a [1]\ny: *a", "x: [1,2,3,4,5,6,7,8,9]"])
def test_unsafe_or_excessively_nested_yaml_is_refused(tmp_path: Path, header: str) -> None:
    (tmp_path / "bad.md").write_text(f"---\n{header}\n---\n", encoding="utf-8")
    result = read_context([tmp_path], redactor=Redactor({}),
                          scope=_scope(tmp_path, max_yaml_depth=4, max_yaml_nodes=10))
    assert not result.complete and result.documents == [] and result.refusals
def test_credentials_and_oversize_files_are_never_returned(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("import openai\n", encoding="utf-8")
    (tmp_path / "large.py").write_text("import openai\n" * 20, encoding="utf-8")
    (tmp_path / "opaque.txt").write_bytes(b"\x00binary")
    result = scan(tmp_path, [], scope=_scope(tmp_path, max_file_bytes=32), redactor=Redactor({}))
    assert not result.complete and result.signals == []
    assert {r.reason for r in result.refusals} == {
        "credential_file", "max_file_bytes", "binary_file"}
@pytest.mark.parametrize("limit", ["max_files", "max_entries", "wall_clock_s"])
def test_file_bound_is_visible(tmp_path: Path, monkeypatch, limit: str) -> None:
    for name in ("a.py", "b.py"):
        (tmp_path / name).write_text("import openai\n", encoding="utf-8")
    if limit == "wall_clock_s":
        from autotester.stages import discover
        ticks = iter([0] + [20] * 100)
        monkeypatch.setattr(discover.time, "monotonic", lambda: next(ticks))
        scope = _scope(tmp_path)
    else:
        scope = _scope(tmp_path, **{limit: 1})
    roots, visited = [tmp_path], []
    if limit == "max_entries":
        roots = [tmp_path / name for name in ("first", "second")]
        for root in roots:
            root.mkdir()
            (root / "app.py").write_text("import openai\n", encoding="utf-8")
        original = Path.iterdir
        def observed(path):
            for child in original(path):
                visited.append(child)
                yield child
        monkeypatch.setattr(Path, "iterdir", observed)
    result = scan(roots[0], roots[1:], scope=scope, redactor=Redactor({}))
    assert not result.complete and result.refusals[-1].reason == limit
    if limit == "max_entries":
        assert len(visited) <= 1, "entry bound is shared across every approved root"
@pytest.mark.parametrize("junction", [False, True])
def test_symlink_escape_is_refused(tmp_path: Path, junction: bool) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "app.py").write_text("import openai\n", encoding="utf-8")
    if junction:
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", "New-Item", "-ItemType",
                        "Junction", "-Path", str(root / "escape"), "-Target", str(outside)],
                       check=True, capture_output=True, timeout=10)
    else:
        (root / "escape").symlink_to(outside, target_is_directory=True)
    result = scan(root, [], scope=_scope(root), redactor=Redactor({}))
    assert not result.complete and result.signals == []
    assert result.refusals[0].reason == "path_escape"
def test_rejected_files_still_consume_physical_read_budget(tmp_path: Path, monkeypatch) -> None:
    import io
    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_text("x" * 100, encoding="utf-8")
    original = Path.open
    physical = []
    class Counted(io.BytesIO):
        def read(self, size=-1):
            raw = super().read(size)
            physical.append(len(raw))
            return raw
    def observed(path, mode="r", *args, **kwargs):
        if mode == "rb" and path.parent == tmp_path:
            with original(path, mode) as stream:
                return Counted(stream.read())
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", observed)
    result = scan(tmp_path, [], redactor=Redactor({}),
                  scope=_scope(tmp_path, max_file_bytes=16, max_total_bytes=20))
    assert sum(physical) <= 20 and not result.complete, "physical read budget covers rejected files"
@pytest.mark.parametrize("secret", ["", "secret-token"])
def test_all_roots_are_preflighted_before_any_open(tmp_path: Path, monkeypatch, secret) -> None:
    from autotester.schema.approval import RunApproval
    from autotester.schema.enums import ApprovalKind
    project, first, second = [tmp_path / name for name in ("project", "first", secret or "second")]
    for root in (project, first, second):
        root.mkdir()
        (root / "app.py").write_text("import openai\n", encoding="utf-8")
    grant = RunApproval(
        project="fixture", run_kind=ApprovalKind.READ, target=str(first.resolve()),
        scope="synthetic read", wall_clock_s=10, granted_by="fixture",
        granted_at="2026-01-01", expires_at="2099-01-01").sign()
    scope = _scope(project).model_copy(update={"approvals": [grant]})
    reads = []
    original = Path.open
    def observed(path, *args, **kwargs):
        reads.append(str(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", observed)
    with pytest.raises(ApprovalRequired, match="refusing to start a read run") as caught:
        scan(project, [first, second], scope=scope, redactor=Redactor({"FIXTURE": secret}))
    assert not secret or secret not in str(caught.value)
    assert caught.value.__suppress_context__
    assert reads == [], "no content is opened before every context root is approved"

@pytest.mark.parametrize("surface", ["literal", "metadata", "filename", "project",
                                    "missing", "scan_open", "context_open"])
@pytest.mark.parametrize("encoded", ["raw", "base64", "hex", "folded"])
def test_secret_keys_tags_and_paths_are_scrubbed(tmp_path, monkeypatch, surface, encoded) -> None:
    import traceback
    secret = "secret-token"
    value = {"base64": base64.b64encode(secret.encode()).decode(),
             "hex": secret.encode().hex(), "folded": "SECRET TOKEN", "raw": secret}[encoded]
    note = tmp_path / ((value if surface == "filename" else secret) + ".py"
                       if surface == "filename" else "note.md")
    content = value if surface == "metadata" else secret
    text = "import openai\n" if surface == "filename" else (
        f"---\n{secret}: {content}\ntags: [{secret}]\n---\n#{secret}\n")
    note.write_text(text, encoding="utf-8")
    scope = _scope(tmp_path).model_copy(
        update={"project": value if surface == "project" else "fixture"})
    redactor = Redactor({"FIXTURE": secret})
    target = tmp_path / value if surface == "missing" else tmp_path
    if surface.endswith("open"):
        def denied(*args, **kwargs):
            raise PermissionError(value)
        monkeypatch.setattr(Path, "open", denied)
    if surface != "literal" and not (encoded == "raw" and surface in {"metadata", "filename"}):
        expected = FileNotFoundError if surface == "missing" else (
            PermissionError if surface.endswith("open") else ValueError)
        with pytest.raises(expected) as caught:
            if surface in {"filename", "missing", "scan_open"}:
                scan(target, [], scope=scope, redactor=redactor)
            else:
                read_context([target], scope=scope, redactor=redactor)
        diagnostic = "".join(traceback.format_exception(caught.value))
        assert redactor.is_clean(diagnostic) and not redactor.contains_folded(diagnostic)
    else:
        result = (scan(target, [], scope=scope, redactor=redactor) if surface == "filename"
                  else read_context([target], scope=scope, redactor=redactor))
        assert secret not in result.model_dump_json()
        assert surface == "filename" or result.documents[0].source.project == "fixture"

def test_discovery_never_calls_provider(tmp_path: Path, monkeypatch) -> None:
    from autotester.providers.base import Provider
    def forbidden(*args, **kwargs):
        raise AssertionError("deterministic read path called a provider")
    monkeypatch.setattr(Provider, "act", forbidden)
    (tmp_path / "prompt.md").write_text("---\ntitle: test\n---\n", encoding="utf-8")
    assert scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({})).complete
    assert read_context([tmp_path], scope=_scope(tmp_path), redactor=Redactor({})).complete
@pytest.mark.parametrize("kinds,expected", [(["sdk"], "conversational"), (["tool"], "agentic"),
    (["sdk", "orchestration"], "orchestration"), (["tool", "orchestration"], "hybrid")])
def test_classification_uses_mock_seam_without_paths(tmp_path: Path, kinds, expected) -> None:
    signals = [Signal(kind=k, evidence_path=str(tmp_path / "app.py"), line=1,
                      detail="Observed fact") for k in kinds]
    provider = MockProvider()
    result = classify_target(signals, provider, scope=_scope(tmp_path), redactor=Redactor({}))
    assert result.system_kind.value == expected and result.signals == signals
    assert len(provider.prompts) == 1 and len(provider.usage) == 1
    assert str(tmp_path) not in provider.prompts[0][1]

def test_non_ai_calls_no_provider_and_unrelated_mock_still_refuses(tmp_path: Path) -> None:
    provider = MockProvider()
    (tmp_path / "math.py").write_text("# import openai\nopenai_count = 2\n", encoding="utf-8")
    found = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert found.complete and found.signals == []
    result = classify_target(found.signals, provider, scope=_scope(tmp_path), redactor=Redactor({}))
    assert result.not_ai_target and result.system_kind is None and provider.prompts == []
    generic = [Signal(kind=k, evidence_path="app.py", line=1, detail="Generic signal")
               for k in ("orchestration", "endpoint", "ground_truth")]
    named = classify_target(generic, provider, scope=_scope(tmp_path), redactor=Redactor({}))
    assert named.not_ai_target
    assert provider.prompts == []
    with pytest.raises(ProviderError):
        provider.act("unrelated")
@pytest.mark.parametrize("bad", ["system_kind", "extra", "confidence", "string", "bool", "nan"])
def test_seeded_bad_classifier_output_is_never_overridden(tmp_path: Path, bad: str) -> None:
    answer = {"system_kind": "agentic", "reason": "fixture", "confidence": 0.5}
    if bad in {"string", "bool", "nan"}:
        answer["confidence"] = {"string": "0.8", "bool": True, "nan": float("nan")}[bad]
    else:
        answer[bad] = "poisoned" if bad != "confidence" else 2.0
    provider = MockProvider(responses={"agent": [answer]})
    signal = Signal(kind="sdk", evidence_path="fixture.py", line=1, detail="SDK import")
    with pytest.raises(ValueError, match="invalid classification response"):
        classify_target([signal], provider, scope=_scope(tmp_path), redactor=Redactor({}))
    assert len(provider.prompts) == 1

def test_model_reason_is_redacted_and_scanner_evidence_is_preserved(tmp_path: Path) -> None:
    provider = MockProvider(responses={"agent": [
        {"system_kind": "agentic", "reason": "secret-value", "confidence": 0.8}]})
    signal = Signal(kind="sdk", evidence_path="app.py", line=7, detail="SDK import")
    result = None
    with contextlib.suppress(ValueError):
        result = classify_target([signal], provider, scope=_scope(tmp_path),
                                 redactor=Redactor({"FIXTURE": "secret-value"}))
    assert result and result.signals[0] == signal and "secret-value" not in result.reason
    assert "secret-value" not in provider.prompts[0][1]

def test_dirty_signal_is_refused_before_provider(tmp_path: Path) -> None:
    provider = MockProvider()
    signal = Signal(kind="sdk", evidence_path="app.py", line=1, detail="secret-value")
    with pytest.raises(Exception, match="secret"):
        classify_target([signal], provider, scope=_scope(tmp_path),
                 redactor=Redactor({"FIXTURE": "secret-value"}))
    assert provider.prompts == []

def test_all_detector_families_have_exact_line_oracles(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("import chromadb\n@mcp.tool()\ndef tool_fn(): pass\n"
                                    "async def run(): pass\ndef workflow(): pass\n"
                                    "endpoint = 'https://fixture.invalid'\n", encoding="utf-8")
    (tmp_path / "prompt.md").write_text("\nPrompt template\n", encoding="utf-8")
    (tmp_path / "ground_truth.json").write_text("\n{}\n", encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert {(s.kind.value, s.line) for s in result.signals} == {
        ("retrieval", 1), ("tool", 2), ("orchestration", 4), ("orchestration", 5),
        ("endpoint", 6), ("prompt", 2), ("ground_truth", 2)}

def test_non_ai_encoded_root_secret_is_refused(tmp_path: Path) -> None:
    provider = MockProvider()
    scope = _scope(tmp_path).model_copy(update={"project_root": "c2VjcmV0LXZhbHVl"})
    with pytest.raises(Exception, match="secret"):
        classify_target([], provider, scope=scope, redactor=Redactor({"FIXTURE": "secret-value"}))
    assert provider.prompts == []

def test_provider_error_never_echoes_raw_secret(tmp_path: Path, monkeypatch) -> None:
    provider = MockProvider()
    def broken(*args, **kwargs):
        raise ProviderError("malformed response secret-value")
    monkeypatch.setattr(provider, "act", broken)
    with pytest.raises(ValueError, match=r"^invalid classification response$") as caught:
        classify_target([Signal(kind="sdk", evidence_path="app.py", line=1, detail="SDK")],
                 provider, scope=_scope(tmp_path), redactor=Redactor({"KEY": "secret-value"}))
    assert caught.value.__suppress_context__ and "secret-value" not in str(caught.value)
    import traceback
    assert "secret-value" not in "".join(traceback.format_exception(caught.value))
@pytest.mark.parametrize("context", [False, True])
def test_final_parser_overrun_is_not_complete(tmp_path: Path, monkeypatch, context: bool) -> None:
    from autotester.stages import discover
    from autotester.stages import read_context as reader
    clock = [0]
    monkeypatch.setattr(discover.time, "monotonic", lambda: clock[0])
    owner, name = (reader, "_frontmatter") if context else (discover, "_python_facts")
    original = getattr(owner, name)
    def slow(*args):
        value = original(*args)
        clock[0] = 20
        return value
    monkeypatch.setattr(owner, name, slow)
    (tmp_path / ("note.md" if context else "app.py")).write_text(
        "---\ntitle: test\n---\n" if context else "import openai\n", encoding="utf-8")
    result = (read_context([tmp_path], scope=_scope(tmp_path), redactor=Redactor({})) if context
              else scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({})))
    assert not result.complete and result.refusals[-1].reason == "wall_clock_s"
