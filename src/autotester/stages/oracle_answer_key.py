"""The answer-key oracle: answer from the key, compare the score the product shows (MP24).

One job: for each `AnswerKey` (derived from product docs, refused if it cites a benchmark finding,
see `schema/answer_key.py`), perform the key's answers as its role, submit, read the score the
product displays and report `ANSWER_MISMATCH` when it is not the score the key predicts -- for
all-correct answers that is the documented score. An unreadable or missing score is a mismatch too,
never a pass. Deterministic; the finding carries the two numbers and the replayable steps, nothing
the product displayed beyond them. Keys come from `<run_dir>/multi_role/answer_keys.json`; none
declared means nothing to score.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import TypeAdapter

from autotester.schema.answer_key import AnswerKey
from autotester.schema.cross_role_assertion import CrossRoleAssertion
from autotester.schema.multi_role_enums import AssertChannel, Expectation, FindingClass, OracleName
from autotester.schema.multi_role_finding import MultiRoleFinding
from autotester.schema.oracle_context import OracleContext, RoleSessionPort
from autotester.schema.role_step import RoleStep

KEYS_FILE = Path("multi_role") / "answer_keys.json"
LOOK_WINDOW_S = 1.0
_SCORE = re.compile(r"(\d{1,6})(?:\s*(?:/|of|out of)\s*(\d{1,6}))?", re.IGNORECASE)


def parse_score(text: str) -> tuple[int, int | None] | None:
    """`7/10` -> (7, 10); `7` -> (7, None); text with no number -> None."""
    found = _SCORE.search(text)
    if found is None:
        return None
    return int(found.group(1)), (int(found.group(2)) if found.group(2) else None)


def _do(port: RoleSessionPort, key: AnswerKey, action: str, step_id: str) -> None:
    port.perform(RoleStep(id=step_id, role_id=key.role_id, action=action))


def take_quiz(key: AnswerKey, port: RoleSessionPort) -> tuple[list[str], str | None]:
    """Give the key's answers and submit; (the steps done, the displayed score text or None)."""
    actions = [key.open_action] if key.open_action else []
    actions += [i.answer_action for i in key.items] + [key.submit_action]
    for n, action in enumerate(actions):
        _do(port, key, action, f"answer-{key.id}-{n}")
    seen = port.observe(CrossRoleAssertion(
        id=f"score-{key.id}", observer_role_id=key.role_id, channel=AssertChannel.UI,
        expectation=Expectation.PRESENT, target=key.score_selector, within_s=LOOK_WINDOW_S))
    return actions, (seen.detail if seen.matched else None)


def _mismatch(key: AnswerKey, actions: list[str], expected: int, text: str | None,
              ) -> MultiRoleFinding | None:
    """A finding unless the displayed score equals `expected` (and the maximum, when shown)."""
    shown = parse_score(text) if text is not None else None
    if shown is not None and shown[0] == expected and shown[1] in (None, key.max_score):
        return None
    got = "no readable score" if shown is None else (
        f"{shown[0]}/{shown[1]}" if shown[1] is not None else str(shown[0]))
    wrong_max = shown is not None and shown[1] not in (None, key.max_score)
    gap = 1 if shown is None else max(abs(shown[0] - expected), int(wrong_max))
    title = f"score for key {key.id} should be {expected}/{key.max_score}, product shows {got}"
    return MultiRoleFinding(
        finding_id=f"answer-key-{key.id}", oracle=OracleName.ANSWER_KEY,
        finding_class=FindingClass.ANSWER_MISMATCH, role=key.role_id, platform_id=key.platform_id,
        title=title[:200],
        url_template=key.url_template, steps=[f"login {key.role_id}", *actions][:50], count=gap)


def check_key(key: AnswerKey, port: RoleSessionPort) -> list[MultiRoleFinding]:
    actions, text = take_quiz(key, port)
    found = _mismatch(key, actions, key.expected_score(), text)
    return [found] if found is not None else []


def load_keys(run_dir: str) -> list[AnswerKey]:
    path = Path(run_dir) / KEYS_FILE
    if not path.is_file():
        return []
    return TypeAdapter(list[AnswerKey]).validate_python(json.loads(path.read_text("utf-8")))


def _answer_key_oracle(context: OracleContext) -> list[MultiRoleFinding]:
    """The registry entry point (see `schema/oracle_context.py`)."""
    keys = load_keys(context.run_dir)
    if keys and context.port is None:
        raise RuntimeError("the answer-key oracle needs the live session port")
    found: list[MultiRoleFinding] = []
    for key in keys:
        if context.role_ids and key.role_id not in context.role_ids:
            raise ValueError("a key names a role that is not in this scenario")
        found.extend(check_key(key, context.port))
    return found

# The registry calls `run`; `doctor.check_duplicate_definitions` flags a top-level `def run` because
# `doctor.py` has one, so the entry point is bound by assignment (CORE-REQUEST in the manifest).
run = _answer_key_oracle
