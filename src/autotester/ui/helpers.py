"""Shared request-validation and lookup helpers used by every UI route module.

One place for slug/id validation so `ui/app.py`, `ui/routes_runs.py` and
`ui/routes_credentials.py` never each grow their own copy (AT-035's
attribute-injection hole started exactly there).

The credential-guard functions (`_refuse_unsafe_value`, `_refuse_unsafe_
submission`, and their helpers) live in `ui/credential_guard.py` (AT-567 --
split out to keep this file under the C2 line cap) and are re-exported below
so every existing `from autotester.ui.helpers import ...` keeps working.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from fastapi import HTTPException

from autotester.browser.secrets import host_of
from autotester.browser.session import NavigationRefused, check_destination
from autotester.core.paths import repo_root
from autotester.core.redact import PLACEHOLDER_RE
from autotester.schema.enums import Action
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore
from autotester.ui.credential_guard import (
    _credential_variants,
    _refuse_direction_override,
    _refuse_unsafe_submission,
    _refuse_unsafe_value,
)

__all__ = [
    "_credential_variants",
    "_load_project_or_404",
    "_project_slugs",
    "_refuse_direction_override",
    "_refuse_unsafe_submission",
    "_refuse_unsafe_value",
    "_require_project_name",
    "_require_reachable_base_url",
    "_require_reachable_navigate_steps",
    "_require_safe_id",
    "_require_slug",
    "_reserved_temp_path",
]

# Same shape as schema.project.Project.slug's own field pattern -- a slug is a
# single safe path segment, never `..`, `/`, `\`, or a null byte, before it is
# ever handed to ProjectPaths/ProjectStore as a directory name.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
# run/case ids are ulid- or content_id-shaped: alnum plus `_`/`-` only.
_HOSTNAME_RE = re.compile(r"^(?=.*\.)[a-z0-9.-]+$")
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _require_slug(slug: str) -> str:
    if not _SLUG_RE.fullmatch(slug):
        raise HTTPException(400, "invalid project slug")
    return slug


def _require_project_name(name: str) -> str:
    """A project needs a name that is not blank or whitespace (AT-430).

    Held here, once, because it used to live inline in the edit route only. Onboard
    had no copy, so a blank name slipped through the one route that creates
    projects — leaving an empty page heading, a `— AutoTester` tab title and a
    text-less link in the sidebar on every page. The browser's `required` attribute
    was the only guard, and a direct POST ignores it. A rule duplicated across
    routes is a rule one route will eventually forget; both now call this.

    The message never echoes the submitted value (AT-088): a password pasted into
    the wrong field must not come back in the response body or the access log."""
    if not name.strip():
        raise HTTPException(400, "a project needs a name")
    return name


def _require_safe_id(value: str, label: str) -> str:
    if not _SAFE_ID_RE.fullmatch(value):
        raise HTTPException(400, f"invalid {label}")
    return value


def _require_reachable_base_url(base_url: str, domains: list[str]) -> None:
    """Refuse a project whose own `base_url` host is outside its `allowed_domains`.

    AT-058: such a project can never test anything — every run dies at the first
    step with `NavigationRefused`, hours after the mistake was made and with no
    hint that onboarding was where it went wrong. Umesh hit this by typing "all"
    in Allowed domains, meaning "allow everything": it was stored verbatim as a
    literal domain named `all`, and the project was dead on arrival.

    Deliberately NOT solved by teaching `allowed_domains` a wildcard —
    `allowed_domains` is the documented boundary the browser is never allowed to
    cross, and an allow-anything escape hatch is a security decision, not a
    validation fix.
    """
    host = host_of(base_url)
    if not host:
        # AT-088: never echo the submitted URL -- this check runs BEFORE the
        # credential guard, so a password pasted here would be handed straight
        # back in the response body and the access log (the fourth occurrence
        # of the AT-068/AT-075 pattern).
        raise HTTPException(400, "that is not a URL the browser can open")
    probe = Project(slug="probe", name="probe", base_url=base_url, allowed_domains=domains)
    if not probe.allows_domain(host):
        # AT-088: `host_of` returns a pseudo-host for garbage, so naming it
        # unconditionally would echo back a credential pasted into this box.
        # Name it only when it is genuinely hostname-shaped; otherwise say what
        # is wrong without quoting what was sent.
        if _HOSTNAME_RE.fullmatch(host):
            raise HTTPException(400, (
                f"this project could never run: its base URL host '{host}' is not covered "
                f"by allowed domains {domains}. Add '{host}' to the allowed domains."
            ))
        raise HTTPException(400, (
            "that base URL does not look like an address the browser can open. Enter the "
            "product's URL, e.g. https://app.example.com/signin."
        ))


def _require_reachable_navigate_steps(steps: list[Step], project: Project) -> None:
    """Refuse a case whose navigate step could never run (AT-432) — AT-058's
    dead-on-arrival class, one level below the project's base URL.

    Decided by `check_destination`, the function that refuses the step at run
    time, so creation and execution cannot disagree. `{{SECRET:KEY}}` targets are
    skipped: the whole target may be a placeholder (AT-076), gated at run time
    against its own domains. The message is ours, not `check_destination`'s,
    which names the host unconditionally — `host_of` returns a pseudo-host for
    garbage, so a pasted credential would echo back (AT-088)."""
    for step in steps:
        if step.action is not Action.NAVIGATE or PLACEHOLDER_RE.search(step.target):
            continue
        try:
            check_destination(project, step.target)
        except NavigationRefused as exc:
            host = host_of(step.target)
            if host and _HOSTNAME_RE.fullmatch(host):
                raise HTTPException(400, (
                    f"this case could never run: step {step.order} navigates to '{host}', which "
                    f"is not covered by allowed domains {project.allowed_domains}."
                )) from exc
            raise HTTPException(400, f"this case could never run: step {step.order} needs a "
                                     "full URL, e.g. https://app.example.com/signin.") from exc


def _project_slugs() -> list[str]:
    projects_dir = repo_root() / "projects"
    if not projects_dir.exists():
        return []
    return sorted(p.name for p in projects_dir.iterdir() if (p / "project.json").exists())


def _load_project_or_404(slug: str) -> tuple[ProjectStore, Project]:
    _require_slug(slug)
    store = ProjectStore(slug)
    project = store.load_project()
    if project is None:
        raise HTTPException(404, f"no project '{slug}'")
    return store, project


def _reserved_temp_path(suffix: str, directory: Path | None = None) -> Path:
    """Reserve a unique filename via mkstemp, then hand it to the exporter to
    create fresh — the exporters all write a brand-new file, so the
    mkstemp-opened fd is closed and the placeholder removed immediately.

    Lives here rather than in one route module because three download routes
    now need it (run report, portable HTML, crawl report) — C3.
    """
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=suffix, dir=directory)
    os.close(fd)
    path = Path(tmp)
    path.unlink()
    return path
