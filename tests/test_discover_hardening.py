"""Committed defenders for the T-151 discovery bounds, line numbering and refusals."""

from pathlib import Path

import pytest

from autotester.core.redact import Redactor
from autotester.schema.ai_target import ReadScope, ScanLimits
from autotester.stages import discover
from autotester.stages.discover import scan
from autotester.stages.read_context import read_context


def _scope(root: Path, **limits: object) -> ReadScope:
    return ReadScope(project="fixture", project_root=str(root), limits=ScanLimits(**limits))


def _reasons(result) -> list[str]:
    return [r.reason for r in result.refusals]


def test_reader_signal_lines_match_exact_source(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("---\ntitle: t\ntags: [a]\n---\n\n#alpha\ntext #beta\n", encoding="utf-8")
    result = read_context([tmp_path], scope=_scope(tmp_path), redactor=Redactor({}))
    tags = {s.line for s in result.signals if s.detail == "Markdown tag"}
    meta = {s.line for s in result.signals if s.detail == "Frontmatter metadata"}
    assert result.complete and tags == {6, 7}
    assert {2, 3} <= meta <= {2, 3, 4}


def test_unicode_and_formfeed_separators_do_not_shift_reader_lines(tmp_path: Path) -> None:
    (tmp_path / "n.md").write_text(
        "---\ntitle: t\n---\nx\u2028y\n#t5\nc\x0cd #t6\rz\r\n#t8\n", encoding="utf-8", newline="")
    result = read_context([tmp_path], scope=_scope(tmp_path), redactor=Redactor({}))
    tags = sorted(s.line for s in result.signals if s.detail == "Markdown tag")
    assert result.complete and tags == [5, 6, 8]


def test_unicode_and_formfeed_separators_do_not_shift_scan_lines(tmp_path: Path) -> None:
    (tmp_path / "prompt.md").write_text("\u2028\nPrompt template\n", encoding="utf-8")
    (tmp_path / "ground_truth.json").write_text("\x0c\n{}\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1  # \u2028\x0c\nimport chromadb\n", encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert {(s.kind.value, s.line) for s in result.signals} == {
        ("prompt", 2), ("ground_truth", 2), ("retrieval", 2)}


def test_scanned_python_is_never_executed(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.sentinel"
    (tmp_path / "app.py").write_text(
        f"open({str(sentinel)!r}, 'w').write('ran')\nendpoint = 'https://fixture.invalid'\n",
        encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert not sentinel.exists(), "scanned code must be parsed, never executed"
    assert [(s.kind.value, s.line) for s in result.signals] == [("endpoint", 2)]


def test_non_markdown_context_files_yield_no_document(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("---\ntitle: t\n---\n#hidden\n", encoding="utf-8")
    result = read_context([tmp_path], scope=_scope(tmp_path), redactor=Redactor({}))
    assert result.complete and result.documents == [] and result.signals == []


@pytest.mark.parametrize("header", ["x: &a [1]\ny: *a", "x: &a [*a]"])
def test_yaml_alias_is_refused_under_generous_limits(tmp_path: Path, header: str) -> None:
    (tmp_path / "bad.md").write_text(f"---\n{header}\n---\n", encoding="utf-8")
    scope = _scope(tmp_path, max_yaml_depth=20, max_yaml_nodes=2000)
    result = read_context([tmp_path], scope=scope, redactor=Redactor({}))
    assert _reasons(result) == ["yaml_alias"] and not result.complete and result.documents == []


def test_tag_flood_is_a_visible_signal_budget_refusal(tmp_path: Path) -> None:
    (tmp_path / "flood.md").write_text("#a " * 20000, encoding="utf-8")
    result = read_context([tmp_path], scope=_scope(tmp_path, max_signals=100),
                          redactor=Redactor({}))
    assert _reasons(result) == ["signal_budget"] and not result.complete
    assert result.signals == [] and result.documents == []


def test_import_flood_is_a_visible_signal_budget_refusal(tmp_path: Path) -> None:
    (tmp_path / "flood.py").write_text("import openai\n" * 500, encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path, max_signals=10), redactor=Redactor({}))
    assert _reasons(result) == ["signal_budget"] and not result.complete
    assert result.signals == []


def test_deadline_is_checked_inside_the_tag_emission_loop(tmp_path: Path, monkeypatch) -> None:
    clock, scrubs = [0.0], [0]
    monkeypatch.setattr(discover.time, "monotonic", lambda: clock[0])
    original = Redactor.scrub

    def slow(self, text):
        scrubs[0] += 1
        clock[0] += 1
        return original(self, text)

    monkeypatch.setattr(Redactor, "scrub", slow)
    (tmp_path / "flood.md").write_text("#a " * 20000, encoding="utf-8")
    result = read_context([tmp_path], scope=_scope(tmp_path, wall_clock_s=5),
                          redactor=Redactor({}))
    assert not result.complete and "wall_clock_s" in _reasons(result)
    assert scrubs[0] < 50, "the deadline must stop emission, not only the final check"


@pytest.mark.parametrize("context", [False, True])
def test_deadline_is_rechecked_after_the_final_redaction(
        tmp_path: Path, monkeypatch, context: bool) -> None:
    clock = [0.0]
    monkeypatch.setattr(discover.time, "monotonic", lambda: clock[0])
    original = Redactor.assert_clean

    def slow(self, text):
        clock[0] += 20
        return original(self, text)

    monkeypatch.setattr(Redactor, "assert_clean", slow)
    (tmp_path / ("n.md" if context else "app.py")).write_text(
        "#tag\n" if context else "import openai\n", encoding="utf-8")
    run = (read_context([tmp_path], scope=_scope(tmp_path), redactor=Redactor({})) if context
           else scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({})))
    assert not run.complete and run.refusals[-1].reason == "wall_clock_s"


def test_deep_binop_chain_is_a_per_file_refusal_and_scan_continues(tmp_path: Path) -> None:
    (tmp_path / "deep.py").write_text("x = " + "a+" * 30000 + "a\n", encoding="utf-8")
    (tmp_path / "ok.py").write_text("import openai\n", encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert _reasons(result) == ["parse_depth"] and not result.complete
    assert [(s.kind.value, s.line) for s in result.signals] == [("sdk", 1)]


def test_deep_decorator_chain_is_a_per_file_refusal_and_scan_continues(tmp_path: Path) -> None:
    (tmp_path / "deep.py").write_text(
        "@a" + ".b" * 600 + "\ndef f(): pass\n", encoding="utf-8")
    (tmp_path / "ok.py").write_text("import openai\n", encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert _reasons(result) == ["parse_depth"] and not result.complete
    assert [(s.kind.value, s.line) for s in result.signals] == [("sdk", 1)]


@pytest.mark.parametrize("name", [".envrc", ".npmrc", ".netrc", ".pypirc", ".htpasswd",
    "keys.jks", "store.keystore", "AuthKey.p8", "id_ecdsa", "credentials.yml",
    "secrets.yaml", "service-account.json", "token.json"])
def test_more_credential_files_are_refused_without_being_opened(
        tmp_path: Path, monkeypatch, name: str) -> None:
    (tmp_path / name).write_text("import openai\n", encoding="utf-8")
    opened = []
    original = Path.open

    def spy(path, *args, **kwargs):
        opened.append(path.name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy)
    result = scan(tmp_path, [], scope=_scope(tmp_path), redactor=Redactor({}))
    assert _reasons(result) == ["credential_file"] and result.signals == []
    assert name not in opened


def test_deadline_is_checked_inside_the_scan_emission_loop(tmp_path: Path, monkeypatch) -> None:
    clock, scrubs = [0.0], [0]
    monkeypatch.setattr(discover.time, "monotonic", lambda: clock[0])
    original = Redactor.scrub

    def slow(self, text):
        scrubs[0] += 1
        clock[0] += 1
        return original(self, text)

    monkeypatch.setattr(Redactor, "scrub", slow)
    (tmp_path / "flood.py").write_text("import openai\n" * 500, encoding="utf-8")
    result = scan(tmp_path, [], scope=_scope(tmp_path, wall_clock_s=5), redactor=Redactor({}))
    assert not result.complete and "wall_clock_s" in _reasons(result)
    assert len(result.signals) < 50 and scrubs[0] < 50, (
        "the deadline must stop scan emission per Signal, not only the final check")
