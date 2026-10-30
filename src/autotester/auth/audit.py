"""The audit trail (AU22): one JSON line per state-changing request in
`<data root>/.work/audit.jsonl`, plus actor/target/action lines for admin actions.

Lines carry no body, query string, password, cookie or hash; callers pass only the
fields named here.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime

from autotester.core.paths import repo_root
from autotester.store.filestore import append_path

_LOCK = threading.Lock()


def _append(row: dict[str, object]) -> None:
    path = repo_root() / ".work" / "audit.jsonl"
    line = json.dumps({"ts": datetime.now(UTC).isoformat(), **row}, ensure_ascii=False)
    with _LOCK:
        append_path(path, line + "\n")


def record_request(email: str, method: str, template: str, status: int) -> None:
    """`template` is the route template (`/projects/{slug}/run`), never the raw URL."""
    _append({"email": email, "method": method, "path": template, "status": status})


def record_action(actor: str, target: str, action: str) -> None:
    _append({"actor": actor, "target": target, "action": action})
