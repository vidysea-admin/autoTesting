"""Inspect approved bounded file trees for deterministic, cited lexical signals."""

import ast
import json
import stat
import time
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

from pydantic import ValidationError

from autotester.core.consent import ApprovalRequired, require_approval
from autotester.core.redact import Redactor
from autotester.providers.base import Provider, ProviderError
from autotester.schema.ai_target import (
    AiTarget,
    Classification,
    Discovery,
    ReadRefusal,
    ReadScope,
    Signal,
)
from autotester.schema.enums import ApprovalKind
from autotester.stages.credential_files import is_credential
from autotester.stages.text_lines import first_nonblank_line

_SDK = {"openai", "anthropic", "google.genai", "google.generativeai"}
_FRAMEWORKS = {"langgraph", "langchain", "autogen", "crewai"}
_RETRIEVAL = {"chromadb", "faiss", "pinecone", "qdrant_client"}
_EXCLUDED = {".git", ".venv", "node_modules", "__pycache__"}


def approved_roots(paths: list[Path], scope: ReadScope, redactor: Redactor) -> list[Path]:
    """Preflight every requested root before any file content is opened."""
    redactor.assert_clean(scope.project)
    try:
        project = Path(scope.project_root).resolve(strict=True)
        roots = sorted({p.resolve(strict=True) for p in paths})
    except OSError as error:
        category = (type(error) if isinstance(error, (FileNotFoundError, PermissionError))
                    else OSError)
        raise category("filesystem access refused") from None
    for root in roots:
        if not root.is_dir():
            raise ValueError("discovery root must be a directory")
        if not root.is_relative_to(project):
            try:
                require_approval(
                    scope.approvals,
                    project=scope.project,
                    kind=ApprovalKind.READ,
                    target=str(root),
                    wall_clock_s=scope.limits.wall_clock_s,
                )
            except ApprovalRequired:
                raise ApprovalRequired("refusing to start a read run: approval required") from None
    return [root for root in roots if not any(
        root != other and root.is_relative_to(other) for other in roots)]


def _refuse(result: Discovery, path: Path, reason: str, redactor: Redactor) -> None:
    result.refusals.append(ReadRefusal(evidence_path=redactor.scrub(str(path)), reason=reason))


def _candidates(
    root: Path,
    scope: ReadScope,
    result: Discovery,
    redactor: Redactor,
    started: float,
    entries: list[int],
) -> Iterator[Path]:
    """Walk directories without following links or leaving the approved root."""
    pending = [root]
    while pending:
        parent = pending.pop()
        children = []
        for child in islice(parent.iterdir(), scope.limits.max_entries - entries[0]):
            entries[0] += 1
            if time.monotonic() - started >= scope.limits.wall_clock_s:
                _refuse(result, parent, "wall_clock_s", redactor)
                return
            if entries[0] > scope.limits.max_entries:
                _refuse(result, parent, "max_entries", redactor)
                return
            children.append(child)
        if entries[0] >= scope.limits.max_entries:
            _refuse(result, parent, "max_entries", redactor)
            return
        for path in sorted(children):
            resolved = path.resolve()
            attrs = getattr(path.lstat(), "st_file_attributes", 0)
            if not resolved.is_relative_to(root) or attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                _refuse(result, path, "path_escape", redactor)
                continue
            if path.is_dir():
                if path.name in _EXCLUDED:
                    continue
                if len(path.relative_to(root).parts) > scope.limits.max_tree_depth:
                    _refuse(result, path, "max_tree_depth", redactor)
                else:
                    pending.append(path)
            else:
                yield path


def bounded_files(
    roots: list[Path], scope: ReadScope, result: Discovery, redactor: Redactor
) -> Iterator[tuple[Path, str]]:
    """Read bounded UTF-8 files after candidate containment and credential checks."""
    started, count, total = time.monotonic(), 0, 0
    entries = [0]
    for root in roots:
        if entries[0] >= scope.limits.max_entries:
            _refuse(result, root, "max_entries", redactor)
            return
        for path in _candidates(root, scope, result, redactor, started, entries):
            if time.monotonic() - started >= scope.limits.wall_clock_s:
                _refuse(result, path, "wall_clock_s", redactor)
                return
            if is_credential(path):
                _refuse(result, path, "credential_file", redactor)
                continue
            if count >= scope.limits.max_files:
                _refuse(result, path, "max_files", redactor)
                return
            count += 1
            remaining = scope.limits.max_total_bytes - total
            if remaining <= 0:
                _refuse(result, path, "max_total_bytes", redactor)
                return
            limit = min(scope.limits.max_file_bytes + 1, remaining)
            with path.open("rb") as stream:
                raw = stream.read(limit)
                total += len(raw)
                if time.monotonic() - started >= scope.limits.wall_clock_s:
                    _refuse(result, path, "wall_clock_s", redactor)
                    return
            if len(raw) > scope.limits.max_file_bytes or path.stat().st_size > len(raw):
                reason = "max_total_bytes" if remaining <= limit else "max_file_bytes"
                _refuse(result, path, reason, redactor)
                continue
            if b"\x00" in raw:
                _refuse(result, path, "binary_file", redactor)
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                _refuse(result, path, "non_utf8", redactor)
                continue
            yield path, text
        if entries[0] > scope.limits.max_entries or any(
                r.reason == "wall_clock_s" for r in result.refusals):
            return


def _python_facts(text: str) -> list[tuple[str, int, str]]:
    """Parse imports and registrations without executing scanned Python."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise ValueError("invalid_python") from exc
    facts = []
    for node in ast.walk(tree):
        imports = []
        if isinstance(node, ast.Import):
            imports = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports = [node.module or ""]
        for module in imports:
            if module in _SDK or module.split(".")[0] in _SDK:
                facts.append(("sdk", node.lineno, "LLM SDK import"))
            if module.split(".")[0] in _FRAMEWORKS:
                facts.append(("agent_framework", node.lineno, "Agent framework import"))
            if module.split(".")[0] in _RETRIEVAL:
                facts.append(("retrieval", node.lineno, "Vector store import"))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                name = ast.unparse(decorator)
                if name in {"tool", "mcp.tool()", "mcp.tool", "server.tool()"}:
                    facts.append(("tool", decorator.lineno, "Tool registration"))
            if isinstance(node, ast.AsyncFunctionDef):
                facts.append(("orchestration", node.lineno, "Async function declaration"))
            elif node.name in {"run_pipeline", "orchestrate", "workflow"}:
                facts.append(("orchestration", node.lineno, "Sync workflow declaration"))
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id in {"endpoint", "base_url", "api_url"}
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)
                ):
                    facts.append(
                        ("endpoint", node.lineno, "Endpoint declaration, not verified live")
                    )
    return facts


def _emit(result: Discovery, path: Path, facts: list, scope: ReadScope, redactor: Redactor,
          started: float) -> bool:
    """Append one file's facts within budget; False once the deadline stops the whole scan."""
    if len(result.signals) + len(facts) > scope.limits.max_signals:
        _refuse(result, path, "signal_budget", redactor)
        return True
    for kind, line, detail in facts:
        if time.monotonic() - started >= scope.limits.wall_clock_s:
            _refuse(result, path, "wall_clock_s", redactor)
            return False
        result.signals.append(
            Signal(kind=kind, line=line, detail=detail, evidence_path=redactor.scrub(str(path))))
    return True


def scan(
    root: Path, context_dirs: list[Path], *, scope: ReadScope, redactor: Redactor
) -> Discovery:
    """Collect lexical evidence only; no classifier or endpoint probe is invoked."""
    roots = approved_roots([root, *context_dirs], scope, redactor)
    started = time.monotonic()
    result = Discovery()
    try:
        for path, text in bounded_files(roots, scope, result, redactor):
            try:
                facts = _python_facts(text) if path.suffix == ".py" else []
            except ValueError:
                _refuse(result, path, "invalid_python", redactor)
                continue
            except (RecursionError, MemoryError):
                _refuse(result, path, "parse_depth", redactor)
                continue
            if path.suffix == ".md" and "prompt" in path.stem.lower() and text.strip():
                facts.append(("prompt", first_nonblank_line(text), "Prompt-template file"))
            if path.stem.lower() in {"ground_truth", "golden_set", "golden-set"} and text.strip():
                line = first_nonblank_line(text)
                facts.append(("ground_truth", line, "Ground-truth fixture file"))
            if not _emit(result, path, facts, scope, redactor, started):
                break
    except OSError as error:
        category = (type(error) if isinstance(error, (FileNotFoundError, PermissionError))
                    else OSError)
        raise category("filesystem access refused") from None
    result.signals = sorted(result.signals, key=lambda s: (s.evidence_path, s.line, s.kind))
    redactor.assert_clean(result.model_dump_json())
    if time.monotonic() - started >= scope.limits.wall_clock_s and not any(
            r.reason == "wall_clock_s" for r in result.refusals):
        _refuse(result, root, "wall_clock_s", redactor)
    return result


def classify_target(
    signals: list[Signal], provider: Provider, *, scope: ReadScope, redactor: Redactor
) -> AiTarget:
    """Name a target using signals only; preserve scanner evidence verbatim."""
    for signal in signals:
        redactor.assert_clean(signal.model_dump_json())
    positive = {"sdk", "agent_framework", "tool", "retrieval", "prompt"}
    common = {
        "root_path": redactor.scrub(scope.project_root),
        "signals": signals,
        "has_ground_truth": any(s.kind.value == "ground_truth" for s in signals),
    }
    redactor.assert_clean(common["root_path"])
    if not any(s.kind.value in positive for s in signals):
        return AiTarget(**common, not_ai_target=True, reason="No observed LLM signal")
    kinds = sorted({s.kind.value for s in signals})
    payload = [
        {"kind": kind, "count": sum(s.kind.value == kind for s in signals)} for kind in kinds
    ]
    prompt_path = Path(__file__).parents[1] / "prompts" / "ai_target_classify_v1.md"
    prompt = prompt_path.read_text(encoding="utf-8") + "\nSIGNALS_JSON\n" + json.dumps(payload)
    redactor.assert_clean(prompt)
    try:
        raw = provider.act(prompt, schema=Classification, prompt_file=prompt_path.name)
        data = raw.model_dump() if hasattr(raw, "model_dump") else raw
        named = Classification.model_validate(data)
    except (ValidationError, ValueError, TypeError, ProviderError):
        raise ValueError("invalid classification response") from None
    clean = redactor.scrub(named.reason)
    redactor.assert_clean(clean)
    result = AiTarget(
        **common, system_kind=named.system_kind, confidence=named.confidence, reason=clean
    )
    redactor.assert_clean(result.model_dump_json())
    return result
