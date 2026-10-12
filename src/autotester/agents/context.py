"""The trusted context of a lead-tester run: everything a model may NOT choose.

Project, store, secrets, judge provider and run id are fixed by whoever starts the run. A
tool receives this beside the model's arguments; no args model has a field for any of it, so
a prompt cannot swap the project, widen an approval or pick a different judge. The browser is
opened lazily (`open_session`) so a guard that refuses a call refuses it before any browser
exists.

NOT a schema model: it holds live handles and duplicates no persisted shape (same convention
as `stages/orchestrate.py::StageContext`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from autotester.browser.observe import PageObserver
from autotester.browser.secrets import SecretStore
from autotester.browser.session import BrowserSession
from autotester.core.paths import RepoDocs
from autotester.providers.base import Provider
from autotester.schema.project import Project
from autotester.store.project_store import ProjectStore


@dataclass
class AgentContext:
    """Live, trusted dependencies for one lead-tester run."""

    project: Project
    store: ProjectStore
    secrets: SecretStore
    judge: Provider
    run_id: str
    open_session: Callable[[PageObserver | None], BrowserSession]
    """Builds a session for this run (the caller decides headed/shot dir); called only
    after every guard has passed."""
    docs: RepoDocs = field(default_factory=RepoDocs)
