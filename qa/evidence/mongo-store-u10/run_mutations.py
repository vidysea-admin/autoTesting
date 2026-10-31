"""Run scripts/mutation_check.py with a sandbox that also holds the files U10 mutates.

The stock sandbox copies only scripts/, tests/, src/, pyproject.toml and conftest.py; U10's
subjects are docker/DEPLOY.md, docker/entrypoint.sh, CLAUDE.md, docs/ARCHITECTURE.md (and
.env.example), so this wrapper widens the copy and changes nothing else. Usage, from the repo root:

    uv run python qa/evidence/mongo-store-u10/run_mutations.py qa/evidence/mongo-store-u10/mutations.json
"""

import shutil
import sys
from pathlib import Path

REPO = Path.cwd()
sys.path.insert(0, str(REPO / "scripts"))
import mutation_check as mc  # noqa: E402

_stock = mc._sandbox


def _wide(repo: Path):
    work, owned = _stock(repo)
    for directory in ("docker", "docs"):
        shutil.copytree(repo / directory, work / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("CLAUDE.md", ".env.example", "Dockerfile"):
        if (repo / name).is_file():
            shutil.copy2(repo / name, work / name)
    return work, owned


mc._sandbox = _wide
sys.exit(mc.main(sys.argv[1:]))
