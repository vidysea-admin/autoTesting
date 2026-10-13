"""Print the durable state under a data root as JSON, for a before/after-restart diff (HO4).

Usage: `python scripts/hosting_state_listing.py <data-root> > before.json`, restart or recreate
the container (or the Windows task), run it again into after.json and diff the two. Lists
projects, accounts, groups, the saved server settings and the run-queue entries; no password,
hash, token or secret value is read or printed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def listing(root: Path) -> dict[str, object]:
    os.environ["AUTOTESTER_ROOT"] = str(root)
    from autotester.auth import accounts, db, groups
    from autotester.store.server_settings import settings_path
    from autotester.ui.run_queue import persisted_entries

    projects = root / "projects"
    have_auth = db.store_exists()
    settings = settings_path(root)
    return {
        "projects": sorted(p.name for p in projects.iterdir() if p.is_dir())
        if projects.is_dir() else [],
        "users": sorted(u.email for u in accounts.list_users()) if have_auth else [],
        "groups": sorted(g.name for g in groups.list_groups()) if have_auth else [],
        "settings": json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else None,
        "queue": [{"id": e.id, "project": e.project, "status": e.status.value}
                  for e in persisted_entries()],
    }


if __name__ == "__main__":
    print(json.dumps(listing(Path(sys.argv[1]).resolve()), indent=2, sort_keys=True))
