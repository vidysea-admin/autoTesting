"""Load the repo-root `.env` — one definition, used by every entry point.

AT-228. `ui/app.py` loaded the repo-root `.env`; **no CLI entry point did**. So
`autotester providers` answered `mock` while a working `GEMINI_API_KEY` sat on
disk, and a HUMAN_GATE was filed against a blocker that did not exist. The user
had already supplied the credential and was told the system was waiting on him.

The lesson is not "the CLI forgot a line". It is that *whether this machine has
credentials* was answered differently by two entry points reading the same disk,
and the disagreement was invisible because each was internally consistent. So
this lives in one place (C3) and both callers use it. Parsing is delegated to
`python-dotenv` rather than hand-rolled: the UI already depended on it, and two
parsers for one file format is the same duplication in a smaller costume.

Secrets never pass through here as values — this only populates `os.environ`
from a gitignored file, and `core.redact` remains the gate before any model call.

**It refuses to run inside a test process, and that is load-bearing.** The first
version of this did not, and the suite caught it immediately: every `CliRunner`
invocation ran the CLI callback, which loaded the real `.env` into the shared
test process for good, and four provider tests that assert "no key present"
started passing a real key instead. `ui/app.py` had already solved this by
loading in a lifespan hook rather than at import ("so TestClient(app) never leaks
real .env values into the test process") — moving the load to a CLI callback
re-opened the hole one door over. A repo whose premise is that a secret never
reaches a model, a log or an artifact cannot put real credentials into every
test process as a side effect of testing a CLI.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import dotenv_values

from autotester.core.paths import repo_root

ENV_FILE = ".env"

# The global provider keys (US1) -- server-wide, `settings.manage` only, never a project's.
PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_API_KEY", "OPENAI_API_KEY",
)
SERVER_PREFIX = "AUTOTESTER_"


def key_namespace(slug: str) -> str:
    """`pathlynks` -> `PATHLYNKS_`; `my-app` -> `MY_APP_` (a project's own key prefix)."""
    return re.sub(r"[^A-Z0-9]+", "_", slug.upper()).strip("_") + "_"


def is_server_key(key: str) -> bool:
    """A key the server reads (provider keys, `AUTOTESTER_*`): always exported, not a project's."""
    return key in PROVIDER_KEYS or key.startswith(SERVER_PREFIX)


def project_credentials(root: Path) -> tuple[tuple[str, ...], frozenset[str]]:
    """(namespaces of every project, keys any project declares) read straight from
    `projects/*/project.json`. A project's credential is read from the file by
    `SecretStore` and typed into a page; it is never a setting for this process."""
    prefixes: list[str] = []
    declared: set[str] = set()
    for config in sorted((root / "projects").glob("*/project.json")):
        prefixes.append(key_namespace(config.parent.name))
        try:
            rows = json.loads(config.read_text(encoding="utf-8")).get("secrets", [])
            declared.update(str(row["key"]) for row in rows if isinstance(row, dict))
        except (OSError, ValueError, KeyError, AttributeError):
            continue  # an unreadable project still reserves its namespace
    return tuple(prefixes), frozenset(declared)

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

    Returning the key names makes "which credentials does this machine have" a
    question a caller can answer and a test can assert, instead of something
    each entry point decides for itself.

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
    for key, value in dotenv_values(path).items():
        if not key or not value or os.environ.get(key):
            continue
        if not is_server_key(key) and (key in declared or key.startswith(prefixes)):
            continue
        os.environ[key] = value
        loaded.append(key)
    return loaded


PUBLIC_ENV_KEYS: frozenset[str] = frozenset({
    "PATHLYNKS_USER_LOGIN_URL",
})
"""AT-086: `.env` keys whose value is explicitly declared NOT a credential (a
public URL, not a secret) -- so `ui/helpers.py`'s submission guard can let a
project's own base_url/allowed_domains match one without refusing it, even at
onboarding, before anything is stored to make the AT-078 already-stored
exemption apply.

Declared HERE, in source, on purpose: no HTTP route reads or writes this name
(not a `Project` field, not a `Form`, not `project.json`), so no request can
ever add a real secret's key to it and walk its value past the guard by
calling it public. Widening this list is a code change, reviewed like any
other -- never inferred from behaviour, never a runtime declaration. Every
other masking path (`Redactor.scrub`, `SecretStore.guard_prompt`) still treats
every `.env` value as secret regardless of this list (C5 unchanged) -- only
the UI submission guard's `SecretStore.public_values()` consults it, and only
for a value that appears under NO other, non-public key (see that method)."""
