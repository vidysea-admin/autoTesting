"""AI CAPTURE: exercise one AI endpoint and record what happened. It observes and never decides.

Contract: qa/contracts/ai-target.md AI6-AI7, core-invariants C5/C7, D-018. This module records
facts (the reply, the latency, whether it parsed as JSON, which expected keys were absent). What
those facts MEAN is settled elsewhere: `stages/ai_judge.py` hands them to the independent judge
or to a rule over the recorded numbers. Nothing here builds a verdict.

Gates, in order, all before any byte leaves: a matching signed `RunApproval` for this exact
endpoint (D-018), then no raw secret in any prompt. Every stored string is scrubbed, and the whole
capture must still be clean afterwards, or it is withheld whole (`CaptureWithheld`).

The transport is an injected `send(endpoint, prompt) -> AiReply`. No HTTP client lives here: how
an endpoint authenticates is not decided by this unit.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime

from autotester.core.consent import require_approval
from autotester.core.redact import Redactor
from autotester.schema.ai_check import AiCapture, AiCheckKind, AiExchange, AiReply
from autotester.schema.approval import RunApproval
from autotester.schema.enums import ApprovalKind

Send = Callable[[str, str], AiReply]


class CaptureWithheld(ValueError):
    """A secret survived scrubbing, so the text is refused. Names no value."""


def _scrub_all(redactor: Redactor, texts: list[str]) -> list[str]:
    return [redactor.scrub(t) for t in texts]


def _json_facts(text: str, expected_keys: list[str]) -> tuple[bool, list[str]]:
    """Whether `text` parses as a JSON object, and which expected keys it lacks."""
    try:
        data = json.loads(text)
    except ValueError:
        return False, list(expected_keys)
    if not isinstance(data, dict):
        return False, list(expected_keys)
    return True, [k for k in expected_keys if k not in data]


def _exchange(prompt: str, reply: AiReply | None, error: str | None, latency_s: float,
              expected_keys: list[str], redactor: Redactor) -> AiExchange:
    text = reply.text if reply else ""
    is_json, missing = _json_facts(text, expected_keys) if reply else (False, [])
    return AiExchange(
        prompt=redactor.scrub(prompt), response=redactor.scrub(text),
        status=reply.status if reply else None, latency_s=max(latency_s, 0.0),
        tools_called=_scrub_all(redactor, reply.tools_called) if reply else [],
        handoffs=_scrub_all(redactor, reply.handoffs) if reply else [],
        is_json=is_json, missing_keys=_scrub_all(redactor, missing), error=error)


def _send_one(send: Send, endpoint: str, prompt: str, clock: Callable[[], float],
              ) -> tuple[AiReply | None, str | None, float]:
    """(reply, error type name, seconds). A transport failure is a recorded fact."""
    started = clock()
    try:
        reply: AiReply | None = send(endpoint, prompt)
        error = None
    except Exception as exc:  # any transport failure is an observation
        reply, error = None, type(exc).__name__
    return reply, error, clock() - started


def capture_run(
    *, project: str, endpoint: str, check: AiCheckKind, prompts: list[str], send: Send,
    approvals: list[RunApproval], redactor: Redactor, expected_keys: list[str] | None = None,
    wall_clock_s: float = 60.0, production: bool = False,
    clock: Callable[[], float] = time.monotonic, now: datetime | None = None,
) -> AiCapture:
    """Send each prompt to `endpoint` through `send` and record the observations.

    Raises `ApprovalRequired` (nothing sent) without a covering approval, and
    `CaptureWithheld` (nothing sent, or nothing returned) when a secret would travel or stay."""
    keys = list(expected_keys or [])
    require_approval(approvals, project=project, kind=ApprovalKind.LIVE_CASE, target=endpoint,
                     actions=len(prompts), wall_clock_s=wall_clock_s, production=production,
                     now=now)
    for prompt in prompts:
        if not redactor.is_clean(prompt):
            raise CaptureWithheld("a prompt carries a secret value; nothing was sent")
    started, exchanges = clock(), []
    for prompt in prompts:
        if exchanges and clock() - started >= wall_clock_s:
            break
        reply, error, took = _send_one(send, endpoint, prompt, clock)
        exchanges.append(_exchange(prompt, reply, error, took, keys, redactor))
    result = AiCapture(
        project=project, endpoint=redactor.scrub(endpoint), check=check,
        expected_keys=_scrub_all(redactor, keys), exchanges=exchanges,
        unsent_prompts=len(prompts) - len(exchanges))
    try:
        redactor.assert_clean(result.model_dump_json())
    except ValueError:
        raise CaptureWithheld("a secret survived scrubbing; the capture was withheld") from None
    return result
