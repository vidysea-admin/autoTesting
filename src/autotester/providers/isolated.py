"""ISOLATED_PROVIDER: run a `Provider` call in a killable child process (D-089 item 2, T-177 AF4).

A synchronous `Provider.act` cannot be cancelled: `asyncio.wait_for` over `asyncio.to_thread`
abandons the thread, the thread keeps running, and the event loop's shutdown waits for it. So the
fallback actuator's wall clock was only a promise for cancellable calls. `IsolatedProvider` makes
it a guarantee: each call runs the REAL provider inside a spawned child process and the parent
waits at most the deadline; on expiry the child is terminated (then killed) and a named
`ProviderDeadline` (a `ProviderError`) is raised, so the caller gets control back in bounded time
whatever the vendor client is doing.

Rules this module keeps:
- the provider is built INSIDE the child from a picklable `factory`, so nothing live (client,
  socket, key) crosses the process boundary; the prompt is whatever the caller already passed
  through its secret guard (`core.redact.assert_no_raw_secrets`), this module adds no prompt text
  except a JSON-schema instruction when the schema class cannot be named to the child;
- the deadline covers child start-up too (spawn imports the package), measured on a monotonic clock;
- an exception in the child comes back as a `ProviderError` carrying the original type and message;
- usage rows the child recorded are merged into this provider's `usage`, so cost accounting holds;
- only `act` is isolated (the fallback actuator's role); other roles raise `Unsupported`.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import multiprocessing as mp
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from autotester.providers.base import ModelT, Provider, ProviderError
from autotester.schema.run import ProviderUsage

DEFAULT_DEADLINE_S = 120.0
_KILL_GRACE_S = 2.0
_SchemaRef = tuple[str, str]


class ProviderDeadline(ProviderError):
    """The isolated provider call did not finish inside its deadline; the child was killed."""


def _schema_ref(schema: type[BaseModel]) -> _SchemaRef | None:
    """`(module, qualname)` when the child can import exactly this class, else None."""
    try:
        found: Any = importlib.import_module(schema.__module__)
        for part in schema.__qualname__.split("."):
            found = getattr(found, part)
    except (ImportError, AttributeError):
        return None
    return (schema.__module__, schema.__qualname__) if found is schema else None


def _resolve(ref: _SchemaRef) -> type[BaseModel]:
    found: Any = importlib.import_module(ref[0])
    for part in ref[1].split("."):
        found = getattr(found, part)
    return found


def _child(factory: Callable[[], Provider], conn: Any, prompt: str, ref: _SchemaRef | None,
           prompt_file: str | None, fed_id: str | None) -> None:
    """Entry point of the child process: build the provider, make the one call, send the answer."""
    try:
        provider = factory()
        schema = _resolve(ref) if ref else None
        answer = provider.act(prompt, schema=schema, prompt_file=prompt_file, fed_id=fed_id)
        conn.send(("ok", answer, [u.model_dump() for u in provider.usage]))
    except BaseException as exc:  # every ending must reach the parent as a message
        with contextlib.suppress(Exception):  # unsendable: the parent reports a silent exit
            conn.send(("err", type(exc).__name__, str(exc)))
    finally:
        conn.close()


def _json_schema_note(schema: type[BaseModel]) -> str:
    return ("\n\nAnswer with one JSON object that validates against this JSON schema, and "
            "nothing else:\n" + json.dumps(schema.model_json_schema()))


class IsolatedProvider(Provider):
    """A `Provider` whose `act` runs in a child process that is killed at the deadline."""

    id = "isolated"

    def __init__(self, factory: Callable[[], Provider], *, label: str | None = None,
                 deadline_s: float = DEFAULT_DEADLINE_S,
                 clock: Callable[[], float] = time.monotonic, **options: Any) -> None:
        super().__init__(**options)
        self._factory, self._label, self._clock = factory, label, clock
        self.deadline_s = deadline_s
        self._until: float | None = None
        self.last_process: Any = None
        """The most recent child, kept so a test (or a postmortem) can see it is dead."""

    @property
    def label(self) -> str:
        return self._label or f"{self.id}:{self.options.get('model', 'child')}"

    def bind_deadline(self, until: float | None) -> None:
        """Cap every following call at the absolute `clock()` time `until` (the actuator's wall
        clock), so one invocation can never wait longer than its own bound. None clears it."""
        self._until = until

    def available(self) -> bool:
        return True  # the real provider is built in the child; its own errors come back typed

    def _budget_s(self) -> float:
        left = self.deadline_s if self._until is None else self._until - self._clock()
        return max(0.0, min(self.deadline_s, left))

    def act(self, prompt: str, schema: type[ModelT] | None = None, *,
            prompt_file: str | None = None, fed_id: str | None = None) -> Any:
        ref = _schema_ref(schema) if schema is not None else None
        if schema is not None and ref is None:  # a dynamic class (browser-use builds its own)
            prompt += _json_schema_note(schema)
        budget = self._budget_s()
        if budget <= 0:
            raise ProviderDeadline("provider deadline already reached before the call started")
        message = self._run(prompt, ref, prompt_file, fed_id, budget)
        if message[0] == "err":
            raise ProviderError(f"{message[1]}: {message[2]}")
        self._merge_usage(message[2])
        return message[1]

    def _run(self, prompt: str, ref: _SchemaRef | None, prompt_file: str | None,
             fed_id: str | None, budget: float) -> tuple:
        ctx = mp.get_context("spawn")
        parent, child_end = ctx.Pipe(duplex=False)
        proc = ctx.Process(target=_child, daemon=True, args=(
            self._factory, child_end, prompt, ref, prompt_file, fed_id))
        self.last_process = proc
        proc.start()
        child_end.close()
        try:
            if not parent.poll(budget):
                raise ProviderDeadline(
                    f"provider deadline {budget:g}s reached; the child process was killed")
            return parent.recv()
        except EOFError as exc:
            raise ProviderError("the provider child process exited without an answer") from exc
        finally:
            parent.close()
            self._reap(proc)

    @staticmethod
    def _reap(proc: Any) -> None:
        """Guarantee the child is gone: let a finished one exit, terminate then kill the rest."""
        proc.join(0.2)
        if proc.is_alive():
            proc.terminate()
            proc.join(_KILL_GRACE_S)
        if proc.is_alive():
            proc.kill()
            proc.join(_KILL_GRACE_S)

    def _merge_usage(self, rows: list[dict]) -> None:
        for row in rows:
            usage = ProviderUsage(**row)
            self.record(usage.role, usage.input_tokens, usage.output_tokens)
            with self._usage_lock:  # `record` counted one call; the child may have made more
                for entry in self.usage:
                    if entry.role == usage.role:
                        entry.calls += max(0, usage.calls - 1)
