"""Driver: run scripts/mutation_check.py unchanged, but add docker/ and Dockerfile to its sandbox.

The harness copies only scripts/, tests/, src/ (mutation_check.py `_sandbox`), so a mutation of
docker/entrypoint.sh, or any test that reads it, cannot be collected there. This wrapper adds
the two paths and calls the harness's own `main`; no repo file is edited.
"""
import shutil
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo / "scripts"))
import mutation_check as m  # noqa: E402

_orig = m._sandbox


def _sandbox(r: Path):
    work, owned = _orig(r)
    shutil.copytree(r / "docker", work / "docker", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(r / "Dockerfile", work / "Dockerfile")
    return work, owned


m._sandbox = _sandbox
sys.exit(m.main([sys.argv[2], "--repo", str(repo)]))
