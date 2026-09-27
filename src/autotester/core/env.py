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

import os
from pathlib import Path

from dotenv import dotenv_values

from autotester.core.paths import repo_root

ENV_FILE = ".env"

TEST_MARKER = "PYTEST_CURRENT_TEST"
"""Set by pytest for the duration of every test. Its presence is the signal that
loading real credentials would be a leak rather than a service."""


def load_repo_env(root: Path | None = None) -> list[str]:
    """Load `<repo>/.env` into `os.environ`. Returns the KEYS it set, never values.

    Existing environment variables win: an explicitly exported value is a
    deliberate override and must not be silently replaced by a file.

    Returning the key names makes "which credentials does this machine have" a
    question a caller can answer and a test can assert, instead of something
    each entry point decides for itself."""
    if TEST_MARKER in os.environ:
        return []
    path = (root or repo_root()) / ENV_FILE
    if not path.exists():
        return []

    loaded: list[str] = []
    for key, value in dotenv_values(path).items():
        if not key or not value or key in os.environ:
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
