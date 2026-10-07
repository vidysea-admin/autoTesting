"""Core utility tests. Redaction is a security control, so it is tested hardest.

Encoded/obfuscated-spelling regression tests (AT-347/AT-352/AT-356, three fix
cycles) live in test_redact_obfuscation.py; core.ids tests live in
test_ids.py -- both split out here in AT-352 cycle 3 when this file crossed
the C2 300-line cap.
"""

from __future__ import annotations

import pytest

from autotester.core.ids import APPROVAL_KEY_ENV
from autotester.core.redact import (
    MASK,
    Redactor,
    assert_no_raw_secrets,
    has_placeholder,
    placeholder_keys,
)


def test_redactor_masks_secret_values_anywhere_in_text() -> None:
    redactor = Redactor({"PASSWORD": "hunter2trombone"})
    scrubbed = redactor.scrub("login failed for hunter2trombone at /login")
    assert "hunter2trombone" not in scrubbed
    assert MASK in scrubbed
    assert "PASSWORD" in scrubbed


def test_redactor_masks_longest_value_first() -> None:
    redactor = Redactor({"SHORT": "abcd", "LONG": "abcdefgh"})
    scrubbed = redactor.scrub("value=abcdefgh")
    assert "abcdefgh" not in scrubbed
    assert "LONG" in scrubbed


def test_redactor_walks_nested_structures() -> None:
    redactor = Redactor({"TOKEN": "s3cr3t-token"})
    payload = {"headers": {"auth": "Bearer s3cr3t-token"}, "list": ["s3cr3t-token"]}
    scrubbed = redactor.scrub_obj(payload)
    assert "s3cr3t-token" not in str(scrubbed)


def test_redactor_masks_even_very_short_declared_values() -> None:
    # AT-002: a declared value is known-exact, so no length floor applies.
    redactor = Redactor({"X": "ab"})
    assert "ab" not in redactor.scrub("token=ab")
    assert redactor.scrub("") == ""
    assert Redactor({"EMPTY": ""}).scrub("nothing to mask") == "nothing to mask"


def test_placeholder_helpers_find_secret_keys() -> None:
    text = "fill {{SECRET:PATHLYNKS_EMAIL}} then {{SECRET:PATHLYNKS_PASSWORD}}"
    assert has_placeholder(text)
    assert placeholder_keys(text) == ["PATHLYNKS_EMAIL", "PATHLYNKS_PASSWORD"]


def test_assert_no_raw_secrets_blocks_a_leaking_prompt() -> None:
    assert_no_raw_secrets("safe {{SECRET:PW}}", ["hunter2trombone"])
    with pytest.raises(ValueError, match="raw secret"):
        assert_no_raw_secrets("password is hunter2trombone", ["hunter2trombone"])


@pytest.mark.parametrize("mode", ["new", "stored", "override", "lost", "hidden", "conflict",
                                 "malformed"])
def test_explicit_approval_key_preparation(tmp_path, monkeypatch, mode) -> None:
    from autotester.core.ids import SigningKeyMissing, ensure_approval_key, sign_payload
    from autotester.schema.approval import RunApproval
    from autotester.schema.enums import ApprovalKind

    monkeypatch.delenv(APPROVAL_KEY_ENV, raising=False)
    env = tmp_path / ".env"
    original = "UNRELATED='preserve me'\n"
    if mode in {"stored", "hidden", "conflict"}:
        original += f" export {APPROVAL_KEY_ENV} = 'stored-key'\n"
    if mode in {"hidden", "conflict"}:
        original += f"{APPROVAL_KEY_ENV}='{'' if mode == 'hidden' else 'different'}'\n"
    env.write_text(original, encoding="utf-8")
    if mode == "override":
        monkeypatch.setenv(APPROVAL_KEY_ENV, "process-key")
    row = RunApproval(project="other", run_kind=ApprovalKind.LIVE_CASE, target="https://x.test",
                      scope="other", granted_by="human", granted_at="2026-01-01",
                      expires_at="2026-01-02", signature="lost-signature")
    calls = []
    def history():
        calls.append(True)
        if mode == "malformed":
            raise ValueError("malformed historical row")
        return [row] if mode == "lost" else []
    if mode in {"lost", "hidden", "conflict", "malformed"}:
        with pytest.raises((SigningKeyMissing, ValueError)):
            ensure_approval_key(env, history)
        assert env.read_text(encoding="utf-8") == original
        return
    ensure_approval_key(env, history)
    import os
    selected = os.environ[APPROVAL_KEY_ENV]
    assert selected == {"stored": "stored-key", "override": "process-key"}.get(mode, selected)
    assert sign_payload({"safe": True})
    assert "UNRELATED='preserve me'" in env.read_text(encoding="utf-8")
    assert (len(selected) == 64 and calls == [True]) if mode == "new" else not calls
    if mode != "new":
        assert env.read_text(encoding="utf-8") == original


_KEY_CONTENTION_SCRIPT = """
import sys
from pathlib import Path
from autotester.core.ids import ensure_approval_key, sign_payload
from autotester.ui.env_editor import set_env_value
env = Path(sys.argv[1])
print('ready', flush=True)
sys.stdin.readline()
print('attempt', flush=True)
if sys.argv[2] == 'writer':
    set_env_value(env, 'UNRELATED', 'preserved')
    print('written', flush=True)
else:
    ensure_approval_key(env, lambda: [])
    print(sign_payload({'probe': True}), flush=True)
"""


def _bounded_child_status(child) -> str:
    """A stuck child startup cannot hang the parent at an unbounded pipe read."""
    from queue import Queue
    from threading import Thread

    messages = Queue()
    Thread(target=lambda: messages.put(child.stdout.readline()), daemon=True).start()
    return messages.get(timeout=15).strip()


def test_env_creation_is_coordinated_across_processes(tmp_path, monkeypatch) -> None:
    import os
    import subprocess
    import sys
    from pathlib import Path

    from autotester.browser.secrets import parse_env
    from autotester.ui.env_editor import _env_lock

    monkeypatch.delenv(APPROVAL_KEY_ENV, raising=False)
    env_path = tmp_path / ".env"
    clean = {k: v for k, v in os.environ.items() if k in {"SYSTEMROOT", "PATH", "TEMP", "TMP"}}
    clean.update(PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
                 PYTEST_CURRENT_TEST="scratch key contention", AUTOTESTER_ROOT=str(tmp_path))
    children = []
    try:
        with _env_lock(env_path):
            for role in ["creator", "creator", "writer"]:
                command = [sys.executable, "-c", _KEY_CONTENTION_SCRIPT, str(env_path), role]
                children.append(subprocess.Popen(command,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, env=clean))
            for child in children:
                assert _bounded_child_status(child) == "ready"
                child.stdin.write("go\n")
                child.stdin.flush()
                assert _bounded_child_status(child) == "attempt"
        results = [child.communicate(timeout=15) for child in children]
        assert all(child.returncode == 0 for child in children)
        assert results[0][0].strip() == results[1][0].strip()
        assert results[2][0].strip() == "written"
        assert parse_env(env_path.read_text(encoding="utf-8"))["UNRELATED"] == "preserved"
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
