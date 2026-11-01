"""mongo-store U10 (M28, M48): the deploy guide, the entrypoint's storage warning and the prose.

The guide and the entrypoint describe the same switches the code reads (`AUTOTESTER_STORE`,
`AUTOTESTER_STORE_AREAS`, `PATHLYNKS_MONGO_URI`), so the names and the area list are pinned to the
code, not retyped here. No Mongo, no network.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from autotester.core.env import MONGO_URI_ENV
from autotester.store.mongo_routes import AREAS

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
GUIDE = (ROOT / "docker" / "DEPLOY.md").read_text(encoding="utf-8")
SCRIPT = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8").replace("\r\n", "\n")
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
ARCH = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    nxt = re.search(r"^## ", text[start + len(heading):], re.M)
    return text[start: start + len(heading) + nxt.start()] if nxt else text[start:]


MONGO = _section(GUIDE, "## State store on MongoDB")
CLOUD_RUN = _section(GUIDE, "## Cloud Run (no VNC)")


# --- DEPLOY.md (M28) -------------------------------------------------------------------

def test_guide_names_every_switch_the_code_reads():
    assert MONGO_URI_ENV == "PATHLYNKS_MONGO_URI"
    for name in (MONGO_URI_ENV, "AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS",
                 "AUTOTESTER_APPROVAL_KEY"):
        assert f"`{name}`" in MONGO, name


def test_guide_lists_every_store_area_the_code_routes_in_the_areas_row():
    row = next(r for r in MONGO.splitlines() if r.startswith("| `AUTOTESTER_STORE_AREAS`"))
    for area in AREAS:
        assert f"`{area}`" in row, area


def test_guide_says_auth_moves_only_with_its_own_entry():
    assert "`auth=mongo`" in MONGO
    assert re.search(r"`auth` moves only with its own entry[^.]*global value", MONGO)


def test_guide_says_the_entrypoint_sets_both_variables_for_every_area():  # E8.2 (a)
    assert "The entrypoint selects Mongo when the URI is present" in MONGO
    assert re.search(r"sets BOTH\s+`AUTOTESTER_STORE=mongo` and an `AUTOTESTER_STORE_AREAS` "
                     r"entry for every area", MONGO)
    assert "all nine" in MONGO and "`credentials=mongo`" in MONGO
    assert "the operator does not set them" in MONGO


def test_guide_says_the_selection_is_made_only_on_a_fresh_data_root():  # E8.2 (b)
    assert "only on a fresh data root" in MONGO
    flat = " ".join(MONGO.split())
    for fact in ("set in the process environment", "SQLite auth file exists",
                 "`projects/*/project.json` exists", "prints one line and keeps files",
                 "`autotester store migrate`", "a dry run unless `--apply`"):
        assert fact in flat, fact


def test_guide_says_a_bad_uri_stops_start_up_and_the_old_revision_serves():  # E8.2 (c)
    assert re.search(r"wrong or unreachable URI stops start-up", MONGO)
    assert re.search(r"revision that fails to start does not take\s+traffic", MONGO)
    assert "previous revision keeps serving" in MONGO


def test_guide_gives_the_escape_hatch_in_the_process_environment():  # E8.2 (d)
    assert re.search(r"`AUTOTESTER_STORE=file` in the PROCESS environment", MONGO)
    assert "stays on files" in MONGO


def test_guide_says_to_set_the_first_admin_before_the_first_start():  # E8.2 (e)
    assert ("`AUTOTESTER_FIRST_ADMIN_EMAIL` before the first start on an empty Mongo auth store"
            in MONGO)
    assert "nobody becomes the first admin from a signup" in MONGO
    assert "D-074" in MONGO and "`bootstrap-admin`" in MONGO


def test_guide_says_a_data_root_env_store_choice_does_not_beat_the_platform_uri():  # E8.2 (f)
    assert re.search(r"data-root `\.env` does not turn it off", MONGO)
    assert "`load_repo_env` never replaces an already-set variable" in MONGO


def test_cloud_run_command_pins_one_instance_and_the_guide_says_until_when():
    assert "--max-instances 1" in CLOUD_RUN.split("```")[1]
    assert re.search(r"`--max-instances 1`[^.]*until", MONGO)
    assert "queue" in MONGO and "CAS" in MONGO


def test_guide_keeps_the_gcs_volume_required_while_any_area_is_on_files_and_cites_d125():
    assert "D-125" in MONGO and "G1" in MONGO
    assert re.search(r"`/data` GCS volume stays required while any area is on files", MONGO)
    assert re.search(r"volume stays required while any state area is on files", CLOUD_RUN)
    assert "--add-volume name=data,type=cloud-storage" in CLOUD_RUN
    assert "scratch only" in MONGO


def test_guide_states_fail_closed_and_plain_storage_and_never_a_uri_value():
    assert "no file fallback" in MONGO.lower()
    assert "D-123" in MONGO and "plain" in MONGO
    assert not re.search(r"mongodb(\+srv)?://[^\s<]+@", GUIDE)


# --- entrypoint.sh (M28) ---------------------------------------------------------------

def _functions() -> str:
    out = []
    for name in ("all_state_on_mongo", "warn_if_ephemeral"):
        start = SCRIPT.index(f"{name}() {{")
        out.append(SCRIPT[start:SCRIPT.index("\n}\n", start) + 3])
    return "\n".join(out)


def _run(tmp_path: Path, **extra: str) -> tuple[str, str]:
    """Run only the warning on a container-like filesystem (device of / and the root equal)."""
    (tmp_path / "mounts").write_text("overlay / overlay rw 0 0\n", encoding="utf-8")
    snippet = f"stat() {{ echo 5; }}\n{_functions()}\nwarn_if_ephemeral\necho rc=$?"
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("AUTOTESTER_") and k != MONGO_URI_ENV}
    env.update(AUTOTESTER_ROOT=tmp_path.as_posix(), AUTOTESTER_MOUNTS_FILE=str(tmp_path / "mounts"))
    env.update(extra)
    out = subprocess.run([BASH, "-c", snippet], capture_output=True, text=True, env=env)
    return out.stdout, out.stderr


pytestmark_bash = pytest.mark.skipif(BASH is None, reason="bash not available")


@pytestmark_bash
def test_entrypoint_syntax_is_valid_and_the_helper_cannot_exit():
    out = subprocess.run([BASH, "-n"], input=SCRIPT, text=True, capture_output=True)
    assert out.returncode == 0, out.stderr
    assert "exit " not in _functions()


@pytestmark_bash
@pytest.mark.parametrize("extra", [
    {},                                                        # file backend: volume needed
    {"AUTOTESTER_STORE": "mongo"},                             # auth still on SQLite
    {"AUTOTESTER_STORE_AREAS": "auth=mongo"},                  # every other area on file
    {"AUTOTESTER_STORE": "mongo", "AUTOTESTER_STORE_AREAS": "auth=mongo,queue=file"},
    {"AUTOTESTER_STORE": "mongo", "AUTOTESTER_STORE_AREAS": "credentials=file,auth=mongo"},
    {"AUTOTESTER_STORE": "mongo", "AUTOTESTER_STORE_AREAS": "auth=file"},
    {"AUTOTESTER_STORE": "mongo", "AUTOTESTER_STORE_AREAS": "auth"},
    {"AUTOTESTER_STORE": "file", "AUTOTESTER_STORE_AREAS": "auth=mongo"},
    {"AUTOTESTER_STORE": "Mongo", "AUTOTESTER_STORE_AREAS": "auth=mongo"},   # typo stays loud
])
def test_entrypoint_still_warns_while_any_area_is_on_files(tmp_path, extra):
    out, err = _run(tmp_path, **extra)
    assert "rc=0" in out and "WARNING: storage is not persistent" in err


@pytestmark_bash
@pytest.mark.parametrize("areas", [
    "auth=mongo", " auth = mongo ", "runs=mongo,auth=mongo,,", "runs=mongo,,auth=mongo",
    "auth=mongo,credentials=mongo,queue=mongo"])
def test_entrypoint_is_quiet_once_every_area_is_on_mongo(tmp_path, areas):
    out, err = _run(tmp_path, AUTOTESTER_STORE="mongo", AUTOTESTER_STORE_AREAS=areas)
    assert "rc=0" in out and "WARNING" not in err
    assert "every state area is on Mongo" in out


@pytestmark_bash
def test_entrypoint_never_prints_the_uri(tmp_path):
    canary = "mongodb://user:CANARY-pw-91@host.invalid/"
    out, err = _run(tmp_path, **{MONGO_URI_ENV: canary, "AUTOTESTER_STORE": "mongo"})
    assert "CANARY" not in out + err


def test_entrypoint_message_points_at_the_guide_section():
    assert "docker/DEPLOY.md" in SCRIPT and "Persistent storage" in SCRIPT


# --- CLAUDE.md and ARCHITECTURE.md prose (M48) -----------------------------------------

def test_claude_md_describes_host_matching_as_exact_not_suffix():
    assert "**suffix** match" not in CLAUDE and "host.endswith" not in CLAUDE
    assert "exact-host" in CLAUDE and "AT-651" in CLAUDE


def test_claude_md_credentials_names_the_mongo_store_and_plain_storage():
    block = _section(CLAUDE, "## Credentials (hard boundary)")
    for needle in ("secrets", "browser_sessions", "D-123", "no application-level encryption",
                   "PATHLYNKS_MONGO_URI", "AUTOTESTER_APPROVAL_KEY"):
        assert needle in block, needle
    assert "Values live only in" not in block


def test_architecture_security_and_storage_name_the_mongo_backend_and_stay_in_budget():
    assert len(ARCH.splitlines()) <= 150
    assert "Values live only in" not in ARCH
    sec, sto = _section(ARCH, "## Security"), _section(ARCH, "## Storage")
    assert "secrets" in sec and "D-123" in sec and "AUTOTESTER_APPROVAL_KEY" in sec
    for needle in ("AUTOTESTER_STORE", "AUTOTESTER_STORE_AREAS", "auth=mongo", "mongo_guard",
                   "fails closed", "G1"):
        assert needle in sto, needle
