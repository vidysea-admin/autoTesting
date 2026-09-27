"""The provider seam. Every model call in the system goes through this interface.

Three roles, three methods. A provider implements what it can and declares the
rest unsupported, so a project can mix Gemini for vision with Anthropic for
judging without any stage knowing which is which.
"""

from __future__ import annotations

import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from autotester.core.trace import TraceWriter
from autotester.schema.observation import VisionOptions
from autotester.schema.run import ProviderUsage

ModelT = TypeVar("ModelT", bound=BaseModel)


class ProviderError(RuntimeError):
    """Any provider-side failure, normalised so stages handle one exception type."""


class Unsupported(ProviderError):
    """This provider does not serve this role."""


class Provider(ABC):
    """One model vendor, adapted to the three jobs AutoTester needs.

    Implementations must never receive raw secret values: callers pass prompts
    containing `{{SECRET:KEY}}` placeholders only.
    """

    id: str = "base"

    def __init__(self, **options: Any) -> None:
        self.options = options
        self.usage: list[ProviderUsage] = []
        self.trace: TraceWriter | None = None
        """Attached by a caller (e.g. `stages/orchestrate_runners.py`) when
        this provider is serving a traced run (D-041 phase 1). None by
        default, so untraced use (tests, standalone scripts) costs nothing."""
        self._usage_lock = threading.Lock()
        """AT-569: T-173's parallel fan-out (`ui/routes_runs.py::
        _run_cases_in_parallel`) shares ONE `Provider` (the judge) across N
        worker threads grading concurrently, so `record()`'s `+=` on a shared
        `ProviderUsage` row -- and its own not-matched -> append race -- can
        lose an increment or create a duplicate role row. One lock per
        provider instance, held for the whole accumulate-and-trace critical
        section below."""

    @property
    def label(self) -> str:
        """`id:model` — how one provider CONFIGURATION is named on disk.

        The ensemble runs the same provider class at two models, and a cached
        observation must say which one produced it (`ModelObservation.
        provider_label`). `id` alone cannot: two cache files would collide and
        the second model's answer would silently overwrite the first's."""
        model = self.options.get("model")
        return f"{self.id}:{model}" if model else self.id

    # -- role: vision -------------------------------------------------------
    def see_video(self, path: Path, prompt: str, schema: type[ModelT],
                  options: VisionOptions | None = None, *,
                  prompt_file: str | None = None, fed_id: str | None = None) -> ModelT:
        """Watch a video and return a structured reading of it.

        `options` carries the generation settings a vision call needs (fps,
        seed, resolution) — they belong to the CALL, not the provider, because
        one provider serves several stages that want different ones.
        `prompt_file`/`fed_id` are trace-span metadata (D-041 RT4): the
        prompt-file id this call used, and the case/verdict id it fed —
        forwarded to `record()` by implementations, never required."""
        raise Unsupported(f"{self.id} does not support video understanding")

    # -- role: agent --------------------------------------------------------
    def act(self, prompt: str, schema: type[ModelT] | None = None, *,
            prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        """Reason about browser state and decide the next action or script edit."""
        raise Unsupported(f"{self.id} does not support agent actions")

    # -- role: judge --------------------------------------------------------
    def judge(
        self, prompt: str, schema: type[ModelT], images: list[Path] | None = None, *,
        prompt_file: str | None = None, fed_id: str | None = None,
    ) -> ModelT:
        """Grade evidence against a rubric in a fresh context. `images`, when
        given, are real screenshot files the judge must actually see (not
        just their filenames in `prompt`) — AT-049: a judge that only ever
        reads evidence *descriptions* is grading blind, however plausible
        its reasoning about a filename sounds."""
        raise Unsupported(f"{self.id} does not support judging")

    # -- shared -------------------------------------------------------------
    @abstractmethod
    def available(self) -> bool:
        """True when credentials/binaries for this provider are present."""

    def record(
        self, role: str, input_tokens: int = 0, output_tokens: int = 0, *,
        prompt_file: str | None = None, fed_id: str | None = None,
        latency_s: float = 0.0, retries: int = 0, fallback_hops: int = 0,
    ) -> None:
        """Accumulate usage so a run can report its cost, and — when a
        `TraceWriter` is attached (`self.trace`) — emit this call's LLM-call
        span. This is the ONLY site that appends such a span (D-041 RT5): no
        stage writes one for itself. `prompt_file`/`fed_id`/`latency_s`/
        `retries`/`fallback_hops` are trace metadata only; usage accounting
        below is unchanged from before this span emission was added. AT-569:
        the whole accumulate-and-trace section is one critical section --
        two threads racing here must never both take the "not matched"
        branch for the same role, and the trace line for THIS call must be
        written from the same usage snapshot it just updated."""
        with self._usage_lock:
            matched = False
            for entry in self.usage:
                if entry.role == role:
                    entry.calls += 1
                    entry.input_tokens += input_tokens
                    entry.output_tokens += output_tokens
                    matched = True
                    break
            if not matched:
                self.usage.append(
                    ProviderUsage(
                        provider=self.id,
                        role=role,
                        calls=1,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                )
            if self.trace is not None:
                self.trace.record_llm(
                    provider=self.label, role=role, prompt_file=prompt_file,
                    input_tokens=input_tokens, output_tokens=output_tokens,
                    latency_s=latency_s, retries=retries, fallback_hops=fallback_hops,
                    fed_id=fed_id,
                )


# -- skill prompt loader (T-175/D-041) --------------------------------------
# The ONE reader for a migrated `SKILL.md` prompt: a stage builds its prompt
# text through this before handing it to see_video/act/judge above -- the
# provider seam these three methods already are (SK2). Not a Provider method
# because a prompt is built before a provider is chosen (grade()/expand()/
# ingest_video() all build the string first, then call the role method on
# whichever provider they were given).
_FRONTMATTER_RE = re.compile(
    r"\A---\r?\n(?P<meta>.*?)\r?\n---\r?\n(?:\r?\n)?(?P<body>.*)\Z", re.DOTALL
)
"""The `(?:\\r?\\n)?` after the closing delimiter eats exactly one blank
separator line when the author left one (every migrated SKILL.md does, for
readability) without requiring it -- a SKILL.md with no blank line before its
body parses just as well."""


def load_skill_prompt(skill: str, *, skills_dir: Path | None = None) -> str:
    """Read one Agent-Skills `SKILL.md`'s body -- the migrated prompt's text.

    `skill` is the folder name under `skills_dir` (e.g. "grade"). The body
    returned is everything after the YAML frontmatter's closing `---`,
    byte-identical (post the same universal-newline read every prompt file
    already got via `read_text`) to what the old loose `prompts/*.md` file
    produced (SK3) -- the frontmatter is the only thing added.

    `skills_dir` mirrors `RepoDocs.prompts_dir`'s explicit-override shape
    (AT-137): a caller/test names the tree directly instead of a relocated
    `AUTOTESTER_ROOT` leaking into a path it does not own. Defaults to this
    package's own `skills/` so a caller with no `RepoDocs` at hand still
    resolves correctly.
    """
    base = skills_dir if skills_dir is not None else Path(__file__).resolve().parents[1] / "skills"
    path = base / skill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError(
            f"{path} has no YAML frontmatter -- expected a leading '---' ... '---' "
            f"block (Agent Skills shape, SK1)"
        )
    return match.group("body")
