"""Behavioural tests: run the real docker/entrypoint.sh and the Dockerfile's
/startup-diagnostics.sh with bash in a sandbox (hardcoded paths rewritten, services stubbed)."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash not available; cannot run scripts")

PY_STUB = (
    '#!/bin/sh\nif [ "$1" = "-c" ] || [ "$1" = "--version" ]; then exit 0; fi\n'
    'echo "STUB-ARGS $*"\n'
)


def posix(path: Path) -> str:
    cyg = shutil.which("cygpath")
    if cyg:
        return subprocess.run([cyg, "-u", str(path)], capture_output=True, text=True).stdout.strip()
    return path.as_posix()


def make_stub(path: Path, body: str, executable: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    path.chmod(0o755 if executable else 0o644)
    return path


def sandbox(tmp_path: Path, script: str, repl: dict[str, str]) -> Path:
    """Rewrite only the listed hardcoded absolute paths in the script text."""
    for old, new in repl.items():
        script = script.replace(old, new)
    out = tmp_path / "script.sh"
    out.write_text(script, encoding="utf-8", newline="\n")
    return out


def run(script: Path, tmp_path: Path, *args: str, env: dict | None = None):
    full = {k: v for k, v in os.environ.items() if k != "PORT"}
    full.update(env or {})
    return subprocess.run([BASH, posix(script), *args], capture_output=True, text=True,
                          env=full, timeout=30, cwd=tmp_path)


@pytest.fixture
def entry(tmp_path):
    """Sandboxed entrypoint.sh plus the path of its python stub."""
    root = posix(tmp_path)
    text = (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
    script = sandbox(tmp_path, text, {
        "/opt/venv/bin/python": f"{root}/venv/bin/python", "/opt/uv-python": f"{root}/uv-python",
        "/opt/venv": f"{root}/venv", "/app/docker": f"{root}/app", "/tmp/.X": f"{root}/.X"})
    (tmp_path / "uv-python").mkdir()
    return script, tmp_path / "venv/bin/python"


def test_preflight_fails_126_on_non_executable_python(entry, tmp_path):
    script, py = entry
    make_stub(py, PY_STUB, executable=False)
    if subprocess.run([BASH, "-c", f'[ -x "{posix(py)}" ]']).returncode == 0:
        pytest.skip("filesystem reports a mode-644 file as executable; cannot test non-exec python")
    r = run(script, tmp_path)
    assert r.returncode == 126
    assert "PREFLIGHT FAIL" in r.stderr and "uid=" in r.stderr


def test_preflight_fails_126_when_python_missing(entry, tmp_path):
    script, _ = entry
    r = run(script, tmp_path)
    assert r.returncode == 126
    assert "PREFLIGHT FAIL" in r.stderr and "uid=" in r.stderr


def test_preflight_passes_and_reports_port(entry, tmp_path):
    script, py = entry
    make_stub(py, PY_STUB)
    r = run(script, tmp_path, env={"PORT": "9123"})
    assert r.returncode == 0, r.stderr
    assert "app port=9123 (PORT=9123)" in r.stdout and "tcp:9123" in r.stdout
    r = run(script, tmp_path)
    assert r.returncode == 0 and "app port=8000 (PORT=unset)" in r.stdout and "tcp:8000" in r.stdout


def diag_body() -> str:
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    block = re.search(r"printf '%s\\n' \\\r?\n(.*?)\s*> /startup-diagnostics\.sh", text, re.S)
    assert block, "diagnostics wrapper not found in Dockerfile"
    lines = re.findall(r"^\s*'(.*)' \\\r?$", block.group(1), re.M)
    return "\n".join(lines) + "\n"


def test_diagnostics_wrapper_execs_entrypoint_and_propagates_rc(tmp_path):
    root = posix(tmp_path)
    make_stub(tmp_path / "venv/bin/python", PY_STUB)
    make_stub(tmp_path / "entrypoint.sh", '#!/bin/bash\necho "ENTRYPOINT-RAN $*"\nexit 5\n')
    make_stub(tmp_path / "bin/namei", "#!/bin/sh\nexit 0\n")
    script = sandbox(tmp_path, diag_body(), {
        "/opt/venv/bin/python": f"{root}/venv/bin/python",
        "/entrypoint.sh": f"{root}/entrypoint.sh", "/app/.env": f"{root}/app.env"})
    r = run(script, tmp_path, "bash", "-c", "echo hi; exit 5",
            env={"PATH": f"{root}/bin:{os.environ['PATH']}"})
    assert "EXECUTING APPLICATION ENTRYPOINT" in r.stdout and "ENTRYPOINT-RAN" in r.stdout
    assert r.returncode == 5, r.stderr


# --- E5 (AT-1433): the entrypoint selects the Mongo store when its URI is present ----------

STORE_VARS = ("PATHLYNKS_MONGO_URI", "AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS",
              "AUTOTESTER_AUTH_DIR", "AUTOTESTER_ROOT")
CANARY_URI = "mongodb://canary-user:canary-pass@h/"
SELECT_TAIL = ('select_mongo_store\necho rc=$?\n'
               'echo "STORE=${AUTOTESTER_STORE-UNSET}"\n'
               'echo "AREAS=${AUTOTESTER_STORE_AREAS-UNSET}"')


def _entrypoint_text() -> str:
    return (ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8").replace("\r\n", "\n")


def _select_fn() -> str:
    text = _entrypoint_text()
    start = text.index("select_mongo_store() {")
    return text[start:text.index("\n}\n", start) + 3]


def _select(tmp_path: Path, **extra: str) -> tuple[dict[str, str], str, str]:
    """Run only the selection step; return (the two store variables after it, stdout, stderr)."""
    full = {k: v for k, v in os.environ.items() if k not in STORE_VARS}
    full.update(AUTOTESTER_ROOT=tmp_path.as_posix())
    full.update(extra)
    out = subprocess.run([BASH, "-c", f"{_select_fn()}\n{SELECT_TAIL}"], capture_output=True,
                         text=True, env=full)
    seen = dict(line.split("=", 1) for line in out.stdout.splitlines() if "=" in line)
    assert seen.get("rc") == "0", out.stderr
    return {"STORE": seen["STORE"], "AREAS": seen["AREAS"]}, out.stdout, out.stderr


def test_e5_uri_alone_selects_mongo_for_every_area(tmp_path):
    from autotester.store.mongo_routes import AREAS
    got, _, _ = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    assert got["STORE"] == "mongo"
    assert sorted(got["AREAS"].split(",")) == sorted(f"{a}=mongo" for a in AREAS)
    assert "auth=mongo" in got["AREAS"] and "credentials=mongo" in got["AREAS"]


def test_e5_the_generated_selection_is_one_the_store_accepts(tmp_path, monkeypatch):
    from autotester.auth.store import on_mongo
    from autotester.store.mongo_routes import AREAS, store_selection
    got, _, _ = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    monkeypatch.setenv("AUTOTESTER_STORE", got["STORE"])
    monkeypatch.setenv("AUTOTESTER_STORE_AREAS", got["AREAS"])
    assert store_selection() == dict.fromkeys(AREAS, "mongo") and on_mongo()


@pytest.mark.parametrize("extra", [
    {"AUTOTESTER_STORE": "file"}, {"AUTOTESTER_STORE_AREAS": "blobs=mongo"},
    {"AUTOTESTER_STORE": "mongo"}, {"AUTOTESTER_STORE_AREAS": "auth=file"}])
def test_e5_an_operator_choice_wins_whole_and_is_not_half_merged(tmp_path, extra):
    got, out, _ = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI, **extra)
    assert got["STORE"] == extra.get("AUTOTESTER_STORE", "UNSET")
    assert got["AREAS"] == extra.get("AUTOTESTER_STORE_AREAS", "UNSET")
    assert "operator store selection kept" in out


@pytest.mark.parametrize("uri", [{}, {"PATHLYNKS_MONGO_URI": ""},
                                 {"PATHLYNKS_MONGO_URI": "  \t "}])
def test_e5_no_uri_or_a_blank_one_selects_nothing(tmp_path, uri):
    got, out, err = _select(tmp_path, **uri)
    assert got == {"STORE": "UNSET", "AREAS": "UNSET"} and "Mongo" not in out + err


def test_e5_the_uri_value_is_never_printed(tmp_path):
    for extra in ({}, {"AUTOTESTER_STORE": "file"}):
        _, out, err = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI, **extra)
        assert "canary" not in (out + err).lower()


def _stub_seeing(var: str) -> str:
    return PY_STUB.replace('echo "STUB-ARGS $*"', f'echo "STUB-ARGS $*"; echo "SEEN=[${var}]"')


def test_e5_the_real_script_exports_the_selection_and_leaks_no_uri(entry, tmp_path):
    script, py = entry
    make_stub(py, _stub_seeing("AUTOTESTER_STORE"))
    r = run(script, tmp_path, env={"PATHLYNKS_MONGO_URI": CANARY_URI,
                                   "AUTOTESTER_ROOT": posix(tmp_path)})
    assert r.returncode == 0, r.stderr
    assert "SEEN=[mongo]" in r.stdout
    assert "every state area is on Mongo" in r.stdout and "WARNING: storage" not in r.stderr
    assert "canary" not in (r.stdout + r.stderr).lower()  # nor in the stubbed exec's argv


def test_e5_the_real_script_without_a_uri_selects_nothing(entry, tmp_path):
    script, py = entry
    make_stub(py, _stub_seeing("AUTOTESTER_STORE"))
    r = run(script, tmp_path, env={"AUTOTESTER_ROOT": posix(tmp_path), "PATHLYNKS_MONGO_URI": ""})
    assert r.returncode == 0 and "SEEN=[]" in r.stdout


def test_e5_an_existing_sqlite_user_store_is_not_locked_out(tmp_path, monkeypatch):
    """A-W1: a container that already holds SQLite users and starts with the URI present keeps
    sign-in on SQLite: the selection is skipped, so the user stays reachable."""
    from autotester.auth import accounts
    from autotester.auth.store import auth_store, on_mongo
    from autotester.auth.store_sqlite import SqliteAuthStore
    for name in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS", "AUTOTESTER_AUTH_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AUTOTESTER_ROOT", str(tmp_path))
    accounts.bootstrap_admin("owner@example.test", "correct-horse-battery-1")
    got, out, _ = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    assert got == {"STORE": "UNSET", "AREAS": "UNSET"} and "existing SQLite auth store" in out
    assert not on_mongo() and isinstance(auth_store(), SqliteAuthStore)
    assert accounts.find_user("owner@example.test") is not None


def test_e5_selection_function_cannot_exit_and_is_called_with_or_true():
    assert "exit " not in _select_fn()
    assert "select_mongo_store || true" in _entrypoint_text()
    out = subprocess.run([BASH, "-n"], input=_select_fn(), text=True, capture_output=True)
    assert out.returncode == 0, out.stderr


# --- E8.1: a prior file-store project blocks the automatic selection -------------------------

NOT_SELECTED = "Mongo not auto-selected"
NONE_SET = {"STORE": "UNSET", "AREAS": "UNSET"}
SLUG = "zeta"  # must not occur in a test name, or tmp_path would print it


def _touch(tmp_path: Path, rel: str) -> None:
    f = tmp_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("{}", encoding="utf-8")


def _no_leak(out: str, err: str) -> None:
    both = (out + err).lower()
    assert "canary" not in both and SLUG not in both


@pytest.mark.parametrize("rel", [f"projects/{SLUG}/project.json",
                                 "projects/with space/project.json"])
def test_e8_a_project_file_blocks_the_selection_with_one_line(tmp_path, rel):
    _touch(tmp_path, rel)
    got, out, err = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    assert got == NONE_SET
    assert out.count(NOT_SELECTED) == 1 and "file-store projects" in out
    assert "docker/DEPLOY.md" in out
    _no_leak(out, err)


def test_e8_auth_file_and_project_together_print_exactly_one_line(tmp_path):
    _touch(tmp_path, ".auth/auth.sqlite3")
    _touch(tmp_path, f"projects/{SLUG}/project.json")
    got, out, err = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    assert got == NONE_SET and out.count(NOT_SELECTED) == 1
    assert "SQLite auth store" in out and "file-store projects" not in out
    _no_leak(out, err)


@pytest.mark.parametrize("setup", [
    lambda p: (p / "projects").mkdir(),                              # empty projects/
    lambda p: (p / "projects" / SLUG).mkdir(parents=True),           # slug dir, no project.json
    lambda p: _touch(p, f"projects/{SLUG}/b/project.json"),          # too deep
    lambda p: _touch(p, "project.json"),                             # not under projects/
    lambda p: None,                                                  # no projects/ at all
], ids=["empty-projects", "slug-dir-only", "too-deep", "wrong-level", "no-projects-dir"])
def test_e8_only_a_direct_project_json_counts(tmp_path, setup):
    from autotester.store.mongo_routes import AREAS
    setup(tmp_path)
    got, out, err = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    assert got["STORE"] == "mongo"
    assert sorted(got["AREAS"].split(",")) == sorted(f"{a}=mongo" for a in AREAS)
    assert NOT_SELECTED not in out
    _no_leak(out, err)


def test_e8_a_project_directory_named_project_json_does_not_count(tmp_path):
    (tmp_path / "projects" / SLUG / "project.json").mkdir(parents=True)  # a directory, not a file
    got, _, _ = _select(tmp_path, PATHLYNKS_MONGO_URI=CANARY_URI)
    assert got["STORE"] == "mongo"


def test_e8_the_real_script_keeps_files_for_a_project_and_leaks_nothing(entry, tmp_path):
    script, py = entry
    make_stub(py, _stub_seeing("AUTOTESTER_STORE"))
    _touch(tmp_path, f"projects/{SLUG}/project.json")
    r = run(script, tmp_path, env={"PATHLYNKS_MONGO_URI": CANARY_URI,
                                   "AUTOTESTER_ROOT": posix(tmp_path)})
    assert r.returncode == 0, r.stderr
    assert "SEEN=[]" in r.stdout and NOT_SELECTED in r.stdout
    _no_leak(r.stdout, r.stderr)  # includes the stubbed exec's argv
