"""T-204 fix cycle 1 (P4): the auth state directory never ships in the image, uvicorn
is launched once under the supervisor (its access log is on since D-107), and the auth
settings are documented (keys only) in .env.example."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lines(name: str) -> list[str]:
    return [ln.strip() for ln in (ROOT / name).read_text(encoding="utf-8").splitlines()]


def test_au23_dockerignore_excludes_the_auth_state_at_any_depth() -> None:
    lines = _lines(".dockerignore")
    assert ".auth/" in lines and "**/.auth/" in lines
    assert not any(ln.startswith("!") and ".auth" in ln for ln in lines)


def test_au22_the_container_starts_uvicorn_once_under_the_supervisor() -> None:
    # D-107 (Umesh 2026-10-21): master 5976c832 keeps the uvicorn access log on, so the
    # `--no-access-log` pin is gone; AT-1390 tracks scrubbing query strings and /v/<token>.
    # The exec starts the supervisor; its continued arguments include uvicorn's command.
    script = "\n".join(_lines("docker/entrypoint.sh"))
    logical_lines = re.sub(r"\\\n\s*", " ", script).splitlines()
    launch = [shlex.split(ln) for ln in logical_lines if ln.startswith("exec ")]
    assert len(launch) == 1
    commands = [shlex.split(arg) for arg in launch[0] if "uvicorn" in arg]
    assert len(commands) == 1
    assert commands[0][:4] == ["uv", "run", "uvicorn", "autotester.ui.app:app"]


def test_au5_env_example_documents_the_auth_settings_and_holds_no_value() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in ("AUTOTESTER_FIRST_ADMIN_EMAIL", "AUTOTESTER_SESSION_HOURS",
                "AUTOTESTER_HOSTED", "AUTOTESTER_COOKIE_SECURE"):
        assert re.search(rf"^{key}=$", text, re.M), key
    for limit in ("5 failed logins", "20 per client address", "10 signups", "50,000"):
        assert limit in text, limit
