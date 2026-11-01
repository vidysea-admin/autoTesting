"""Load the repo-root `.env` — one definition, used by every entry point.

AT-228. `ui/app.py` loaded the repo-root `.env`; **no CLI entry point did**. So
`autotester providers` answered `mock` while a working `GEMINI_API_KEY` sat on disk, and a
HUMAN_GATE was filed against a blocker that did not exist. Whether this machine has credentials
lives in one place (C3); parsing is delegated to `python-dotenv`. Secrets never pass through
here as values; `core.redact` remains the gate before any model call.

**It refuses to run inside a test process, and that is load-bearing.** The first version
did not: every `CliRunner` invocation loaded the real `.env` into the shared test process
for good, and provider tests asserting "no key present" started passing a real key.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import IO, Any

from dotenv import dotenv_values

from autotester.core.paths import repo_root

ENV_FILE = ".env"

# The global provider keys (US1) -- server-wide, `settings.manage` only, never a project's.
PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_API_KEY", "OPENAI_API_KEY",
)
# T-169: the AutoTester account the acceptance script signs in as (an admin enters it on the
# settings page; the script reads it through `load_repo_env`). `AUTOTESTER_*`, so a server key.
HARNESS_KEYS = ("AUTOTESTER_HARNESS_EMAIL", "AUTOTESTER_HARNESS_PASSWORD")
SERVER_PREFIX = "AUTOTESTER_"


def key_namespace(slug: str) -> str:
    """`pathlynks` -> `PATHLYNKS_`; `my-app` -> `MY_APP_` (a project's own key prefix)."""
    return re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_") + "_"


def is_server_key(key: str) -> bool:
    """A key the server reads (provider keys, `AUTOTESTER_*`): always exported, not a project's.
    Any letter case: `autotester_approval_key` is the server's key to a case-blind environment."""
    upper = key.upper()
    return upper in PROVIDER_KEYS or upper.startswith(SERVER_PREFIX)


def project_credentials(root: Path) -> tuple[tuple[str, ...], frozenset[str]]:
    """(namespaces of every project, keys any project declares) read straight from
    `projects/*/project.json`. A project's credential is read from the file by
    `SecretStore` and typed into a page; it is never a setting for this process."""
    from autotester.schema.project import SecretDeclarations
    from autotester.store.filestore import exists_path, list_children, read_json  # store imports us

    prefixes: list[str] = []
    declared: set[str] = set()
    projects = root / "projects"
    for name in list_children(projects):
        config = projects / name / "project.json"
        if not exists_path(config):
            continue
        prefixes.append(key_namespace(name))
        try:
            rows = (read_json(config, SecretDeclarations) or SecretDeclarations()).secrets
            declared.update(str(row["key"]) for row in rows if isinstance(row, dict))
        except (OSError, ValueError, KeyError):
            continue  # an unreadable project still reserves its namespace
    return tuple(prefixes), frozenset(declared)

def read_dotenv(source: Path | IO[str]) -> dict[str, str | None]:
    """The ONE reading of a dotenv file or stream: literal, never interpolated (AT-1368).

    `dotenv_values` defaults to `interpolate=True`, which rewrites `${NAME}` inside a value
    (and, for a double-quoted value, decodes `\n`). A credential is data, not a template:
    a password containing `${X}` must reach the login form as typed. Every reader of the
    repo `.env` that wants the VALUE (loader, redaction, tesseract path) calls this."""
    return dotenv_values(source if isinstance(source, Path) else None,
                         stream=None if isinstance(source, Path) else source, interpolate=False)


def dollar_value_keys(root: Path | None = None) -> list[str]:
    """KEY NAMES (never values) of repo-root `.env` entries whose value contains `${` (AT-1389).

    After AT-1368 such a value is kept literally, so a hand-written `${VAR}` that used to
    expand now reaches the login form as typed. The product reports it instead of a human
    grepping the file. Reads through `read_dotenv`, the one parser; no value leaves here."""
    path = (root or repo_root()) / ENV_FILE
    if not path.exists():
        return []
    return sorted(key for key, value in read_dotenv(path).items() if key and "${" in (value or ""))


def dollar_warning(keys: list[str]) -> str:
    """The one sentence doctor and the settings page both show; empty when there is nothing."""
    if not keys:
        return ""
    return (f"{len(keys)} value(s) in the repo-root .env contain \"${{\" and are kept literally "
            f"(no expansion): {', '.join(keys)}. Re-enter them if a ${{VAR}} was meant.")


EPHEMERAL_OK_ENV = "AUTOTESTER_EPHEMERAL_OK"
"""`1` says "this server's data root is deliberately not a volume" (local docker): no warning."""
_MEMORY_FS = frozenset({"tmpfs", "ramfs"})
_MOUNTS = Path("/proc/mounts")


def _device(path: Path) -> int:
    """`st_dev` of `path`, or of its nearest existing ancestor when it is not created yet."""
    while not path.exists() and path != path.parent:
        path = path.parent
    return path.stat().st_dev


def _mount_entries(text: str) -> list[tuple[str, str]]:
    """(mount point, fs type) per `/proc/mounts` line; octal escapes (backslash-040) decoded."""
    out = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            out.append((re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), parts[1]), parts[2]))
    return out


def _holding_mount(base: Path, entries: list[tuple[str, str]]) -> tuple[str, str] | None:
    """The deepest mount whose point is `base` or an ancestor of it: the filesystem it lives on."""
    where = PurePosixPath(base.as_posix())
    held = [e for e in entries if e[0] == "/" or where == PurePosixPath(e[0])
            or PurePosixPath(e[0]) in where.parents]
    return max(held, key=lambda e: len(PurePosixPath(e[0]).parts), default=None)


def on_cloud_run() -> bool:
    """True when `K_SERVICE` (Cloud Run sets it) is non-blank: the one detector (E5.4, C3)."""
    return bool(os.environ.get("K_SERVICE", "").strip())


def _all_areas_mongo() -> bool:
    """Every store area on Mongo, `auth` by its own entry too (A-W1); an invalid selection counts
    as not (a diagnostic never raises)."""
    from autotester.auth.store import on_mongo
    from autotester.store.mongo_routes import store_selection  # lazy: it imports this module
    try:
        return set(store_selection().values()) == {"mongo"} and on_mongo()
    except Exception:
        return False


def storage_warning(root: Path | None = None, mounts_path: Path = _MOUNTS) -> str | None:
    """One sentence when the data root is NOT on a persistent volume, else None.

    A container keeps `AUTOTESTER_ROOT` (auth SQLite, `projects/`, approvals) on its throwaway
    filesystem unless a volume is mounted there, and every deploy then wipes the accounts.
    Ephemeral = the deepest mount holding the root is `/`, is memory backed, or shares `st_dev`
    with `/`. What cannot be determined answers None (this check never stops a start), except on
    Cloud Run (E5.4), where silence is the failure: it warns there, unless every store area is on
    Mongo (the root is then scratch). `AUTOTESTER_EPHEMERAL_OK=1` silences it."""
    cloud, base = on_cloud_run(), root or repo_root()
    try:
        if os.environ.get(EPHEMERAL_OK_ENV, "").strip() == "1" or (cloud and _all_areas_mongo()):
            return None
        base = base.resolve()
        entries = _mount_entries(mounts_path.read_text(encoding="utf-8", errors="replace"))
        if not any(point == "/" for point, _ in entries):
            raise OSError("no / entry in the mount table")
        held = _holding_mount(base, entries)
        ephemeral = (held is None or held[0] == "/" or held[1] in _MEMORY_FS
                     or _device(base) == _device(Path("/")))
    except Exception:  # a diagnostic must never break startup
        return (f"Cannot verify that {base} is a persistent volume: accounts and projects may "
                f"be lost on every deploy. Mount a volume at {base}.") if cloud else None
    if not ephemeral:
        return None
    return (f"Storage is not persistent: accounts and projects are lost on every deploy. "
            f"Mount a volume at {base}.")


TEST_MARKER = "PYTEST_CURRENT_TEST"
"""Set by pytest for the duration of every test. Its presence is the signal that
loading real credentials would be a leak rather than a service."""


def load_repo_env(root: Path | None = None) -> list[str]:
    """Load `<repo>/.env` into `os.environ`. Returns the KEYS it set, never values.

    Existing environment variables win: an explicitly exported value is a
    deliberate override and must not be silently replaced by a file. An EMPTY
    inherited value is not an override but a blank placeholder (a compose
    `env_file` copied from `.env.example` hands the container `KEY=""`), so it
    counts as unset and the file's value loads (AT-863).

    Returning the key names makes "which credentials does this machine have" a question a
    caller can answer and a test can assert, not something each entry point decides alone.

    T-204 AU21: a PROJECT's credentials are not loaded. The file is shared and a project
    route writes into it under a prefix its creator chose (slug `http` + `HTTP_PROXY`,
    `node` + `NODE_OPTIONS`): exporting every key would let that value steer this process,
    a library it loads or a child it starts. Keys a project declares, and keys inside any
    project's namespace (declared or not, so un-declaring leaves nothing to export), stay
    in the file; server keys (`is_server_key`) are always exported."""
    base = root or repo_root()
    if TEST_MARKER in os.environ:
        return []
    path = base / ENV_FILE
    if not path.exists():
        return []

    prefixes, declared = project_credentials(base)
    loaded: list[str] = []
    for key, value in read_dotenv(path).items():
        if not key or not value or os.environ.get(key):
            continue
        if not is_server_key(key) and (key in declared or key.startswith(prefixes)):
            continue
        os.environ[key] = value
        loaded.append(key)
    return loaded


MONGO_URI_ENV = "PATHLYNKS_MONGO_URI"
"""The one name of the state-store connection string (D-120; mongo-store M28, M36)."""


def mongo_uri(root: Path | None = None) -> str:
    """The state-store URI, or `""`: a non-blank process variable, else the repo-root `.env`
    value (the same `read_dotenv` reading as every other `.env` reader). The value is a secret:
    it is returned to the one caller that opens the store and is never logged or echoed.

    A test process with no `AUTOTESTER_ROOT` would read the real code tree's `.env`; it does not,
    so a unit test can never pick up a developer's live URI (same reason `load_repo_env` skips)."""
    live = os.environ.get(MONGO_URI_ENV, "").strip()
    if live:
        return live
    if root is None and TEST_MARKER in os.environ and not os.environ.get("AUTOTESTER_ROOT"):
        return ""
    path = (root or repo_root()) / ENV_FILE
    return (read_dotenv(path).get(MONGO_URI_ENV) or "").strip() if path.is_file() else ""


def credential_collection() -> Any:
    """The `secrets` collection when the credentials area is on mongo, else `None` (file mode: no
    driver is imported, M13). The ONE place the collection is named (M31); the write door is
    `ui/env_editor.py`. No encryption and no key (D-123, M32)."""
    from autotester.store.mongo_routes import store_selection  # lazy: it imports this module

    if store_selection()["credentials"] != "mongo":
        return None
    from autotester.store.mongo_backend import default_store

    return default_store().collection("secrets")


def stored_secret_values() -> dict[str, str]:
    """Key -> value of every stored credential, any project; `{}` when the area is on file."""
    coll = credential_collection()
    return {} if coll is None else {d["_id"]: d["value"] for d in coll.find({})}


def redaction_values(file_values: Mapping[str, str]) -> dict[str, str]:
    """`file_values` plus every stored value under a `KEY@store` label, so a key held in both
    places keeps both values masked (M8, M34)."""
    return {**file_values, **{f"{k}@store": v for k, v in stored_secret_values().items()}}


def resolve_credentials(file_values: Mapping[str, str], slug: str,
                        declared: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    """`(usable, shadow)` for one project. Store off: exactly the `.env` values, as ever. Store on
    (M33): this project's own stored value beats the process environment, which beats the file.
    Every value a layer hides, and every other project's, stays in `shadow` (masked, never
    resolvable); a project resolves only the keys it declares."""
    values, extra = dict(file_values), {}
    coll = credential_collection()
    if coll is not None:
        docs = coll.find({})
        own = {d["_id"]: d["value"] for d in docs if d.get("p") == slug and d["_id"] in declared}
        for layer in ({k: os.environ[k] for k in declared if os.environ.get(k)}, own):
            for key, value in layer.items():
                if values.get(key) not in (None, "", value):
                    extra[f"{key}@{len(extra)}"] = values[key]
                values[key] = value
        extra.update({f"{d['_id']}@{d.get('p')}": d["value"] for d in docs
                      if d["_id"] not in own})
    usable = {k: v for k, v in values.items() if k in declared and v}
    return usable, {**extra, **{k: v for k, v in values.items() if k not in declared and v}}


PUBLIC_ENV_KEYS: frozenset[str] = frozenset({
    "PATHLYNKS_USER_LOGIN_URL",
})
"""AT-086: `.env` keys whose value is declared NOT a credential (a public URL), so
`ui/helpers.py`'s submission guard can let a project's own base_url/allowed_domains match one
without refusing it, even at onboarding.

Declared HERE, in source, on purpose: no HTTP route reads or writes this name (not a `Project`
field, `Form` or `project.json`), so no request can add a real secret's key to it. Widening it
is a reviewed code change. Every other masking path (`Redactor.scrub`, `SecretStore.guard_prompt`)
still treats every `.env` value as secret (C5) -- only `SecretStore.public_values()` consults
it, and only for a value that appears under NO other, non-public key."""
