"""Read approved Markdown as metadata only, never a vault graph or body corpus."""

import hashlib
import re
import time
from pathlib import Path

import yaml
from yaml.events import AliasEvent, CollectionEndEvent, CollectionStartEvent, ScalarEvent

from autotester.core.redact import Redactor
from autotester.schema.ai_target import ContextDocument, Discovery, ReadRefusal, ReadScope, Signal
from autotester.schema.enums import SourceKind
from autotester.schema.project import Source
from autotester.stages.discover import approved_roots, bounded_files
from autotester.stages.text_lines import split_lines


def _frontmatter(text: str, scope: ReadScope) -> tuple[dict, int]:
    """Bound YAML before loading; aliases and explicit executable tags are refused."""
    lines = split_lines(text)
    if not lines or lines[0] != "---":
        return {}, 0
    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    if end is None:
        raise ValueError("unterminated_frontmatter")
    payload = "\n".join(lines[1:end])
    depth = 0
    for count, event in enumerate(yaml.parse(payload), 1):
        if count > scope.limits.max_yaml_nodes:
            raise ValueError("max_yaml_nodes")
        if isinstance(event, AliasEvent):
            raise ValueError("yaml_alias")
        if isinstance(event, CollectionStartEvent):
            depth += 1
        if isinstance(event, CollectionEndEvent):
            depth -= 1
        if depth > scope.limits.max_yaml_depth:
            raise ValueError("max_yaml_depth")
        if isinstance(event, (ScalarEvent, CollectionStartEvent)) and event.tag:
            raise ValueError("explicit_yaml_tag")
    data = yaml.safe_load(payload) or {}
    if not isinstance(data, dict) or any(not isinstance(k, str) for k in data):
        raise ValueError("frontmatter_must_be_string_keyed_mapping")
    return data, end


def _metadata(value: object, redactor: Redactor, seen: frozenset[int] = frozenset()) -> object:
    """Normalize safe metadata types and redact keys as well as values; a cycle is an alias."""
    if isinstance(value, (dict, list)):
        if id(value) in seen:
            raise ValueError("yaml_alias")
        seen = seen | {id(value)}
    if isinstance(value, dict):
        return {redactor.scrub(str(k)): _metadata(v, redactor, seen) for k, v in value.items()}
    if isinstance(value, list):
        return [_metadata(v, redactor, seen) for v in value]
    if isinstance(value, str):
        return redactor.scrub(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return redactor.scrub(str(value))


def _guard(emitted: int, scope: ReadScope, started: float) -> None:
    """Refuse before the next Signal once the signal or time budget is spent."""
    if emitted >= scope.limits.max_signals:
        raise ValueError("signal_budget")
    if time.monotonic() - started >= scope.limits.wall_clock_s:
        raise ValueError("wall_clock_s")


def _document(path: Path, text: str, scope: ReadScope, redactor: Redactor,
              started: float, used: int = 0) -> ContextDocument:
    """Extract only metadata and standalone hashtag tokens outside fenced blocks."""
    frontmatter, end = _frontmatter(text, scope)
    signals, tags = [], []
    declared = frontmatter.get("tags", [])
    if isinstance(declared, str):
        declared = [declared]
    if not isinstance(declared, list) or any(not isinstance(t, str) for t in declared):
        raise ValueError("tags_must_be_strings")
    tags.extend(redactor.scrub(t) for t in declared)
    fenced = False
    for line, value in enumerate(split_lines(text), 1):
        if line <= end + 1 and end:
            if line > 1 and value.strip():
                _guard(used + len(signals), scope, started)
                signals.append(
                    Signal(
                        kind="context",
                        evidence_path=redactor.scrub(str(path)),
                        line=line,
                        detail="Frontmatter metadata",
                    )
                )
            continue
        if value.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        if not fenced:
            for tag in re.findall(r"(?<![\w\[])#([\w/-]+)\b", value):
                _guard(used + len(signals), scope, started)
                tags.append(redactor.scrub(tag))
                signals.append(
                    Signal(
                        kind="context",
                        evidence_path=redactor.scrub(str(path)),
                        line=line,
                        detail="Markdown tag",
                    )
                )
    source = _source_reference(path, text, scope, redactor)
    return ContextDocument(
        evidence_path=redactor.scrub(str(path)),
        source=source,
        frontmatter=_metadata(frontmatter, redactor),
        tags=sorted(set(tags)),
        signals=signals,
    )


def _source_reference(path: Path, text: str, scope: ReadScope, redactor: Redactor) -> Source:
    """Keep only a valid project-relative source path; external refs are unpersisted."""
    project_root = Path(scope.project_root).resolve()
    relative = str(path.relative_to(project_root)) if path.is_relative_to(project_root) else None
    if relative is not None and redactor.scrub(relative) != relative:
        relative = None
    return Source(project=scope.project, kind=SourceKind.DOC, path=relative,
                  label=redactor.scrub(path.name), sha256=hashlib.sha256(text.encode()).hexdigest())


def _reason(exc: Exception) -> str:
    if isinstance(exc, (RecursionError, MemoryError)):
        return "parse_depth"
    return str(exc) if isinstance(exc, ValueError) else "invalid_yaml"


def read_context(roots: list[Path], *, scope: ReadScope, redactor: Redactor) -> Discovery:
    """Extract metadata from approved trees without evaluating Markdown body syntax."""
    result = Discovery()
    checked = approved_roots(roots, scope, redactor)
    started = time.monotonic()
    try:
        for path, text in bounded_files(checked, scope, result, redactor):
            if path.suffix.lower() != ".md":
                continue
            try:
                document = _document(path, text, scope, redactor, started, len(result.signals))
            except (ValueError, yaml.YAMLError, RecursionError, MemoryError) as exc:
                result.refusals.append(
                    ReadRefusal(evidence_path=redactor.scrub(str(path)),
                                reason=redactor.scrub(_reason(exc))))
                continue
            result.documents.append(document)
            result.signals.extend(document.signals)
    except OSError as error:
        category = (type(error) if isinstance(error, (FileNotFoundError, PermissionError))
                    else OSError)
        raise category("filesystem access refused") from None
    redactor.assert_clean(result.model_dump_json())
    if time.monotonic() - started >= scope.limits.wall_clock_s and not any(
            r.reason == "wall_clock_s" for r in result.refusals):
        result.refusals.append(ReadRefusal(evidence_path="context", reason="wall_clock_s"))
    return result
