"""The container's data root is AUTOTESTER_ROOT (HO3): defaulted to /data only when unset and /app
is read-only; dev compose pins it to the writable /app mount so state survives recreate (D6)."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="bash not installed")


def _block() -> str:
    text = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
    return text[text.index("# The data root is AUTOTESTER_ROOT"):text.index("# Readiness sockets")]


def _run(tmp_path: Path, app: str, root: str | None) -> str:
    script = tmp_path / "blk.sh"
    tail = 'echo "ROOT=${AUTOTESTER_ROOT:-}"'
    body = "\n".join(["set -eu", _block().replace("/app", app), tail, ""])
    script.write_text(body, encoding="utf-8", newline="\n")
    env = {"PATH": subprocess.os.environ["PATH"]}
    if root is not None:
        env["AUTOTESTER_ROOT"] = root
    out = subprocess.run([BASH, script.as_posix()], capture_output=True, text=True, env=env,
                         timeout=30)
    return out.stdout.strip().splitlines()[-1]


@needs_bash
def test_unset_and_readonly_app_defaults_to_data(tmp_path):
    assert _run(tmp_path, (tmp_path / "missing-app").as_posix(), None) == "ROOT=/data"


@needs_bash
def test_writable_app_mount_keeps_repo_root_behaviour(tmp_path):
    assert _run(tmp_path, tmp_path.as_posix(), None) == "ROOT="


@needs_bash
def test_operator_value_is_never_overridden(tmp_path):
    ro = (tmp_path / "missing-app").as_posix()
    assert _run(tmp_path, ro, (tmp_path / "x").as_posix()) == f"ROOT={(tmp_path / 'x').as_posix()}"


def test_dev_compose_pins_root_to_the_mounted_app():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    svc = yaml.safe_load(text)["services"]["autotester"]
    assert ".:/app" in svc["volumes"] and "AUTOTESTER_ROOT=/app" in svc["environment"]


def test_prod_overlay_and_entrypoint_reference_data():
    prod = (ROOT / "docker/compose.prod.yml").read_text(encoding="utf-8")
    assert re.search(r"AUTOTESTER_ROOT:\s*/data", prod)
    entry = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")
    assert "export AUTOTESTER_ROOT=/data" in entry


def test_gemini_cache_is_under_the_data_root():
    src = (ROOT / "src/autotester/providers/gemini.py").read_text(encoding="utf-8")
    assert 'Path(".work' not in src and "work_dir()" in src
