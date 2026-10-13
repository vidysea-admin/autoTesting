"""Test helper: make a directory or file link when the host allows it, else fall back or skip.

Creating symlinks on Windows needs a privilege (WinError 1314) most dev and CI
hosts lack. A directory link falls back to an NTFS junction, which the code
under test must refuse just the same; a file link has no junction equivalent,
so that case skips with the reason instead of failing on a host limit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def link_dir(link: Path, target: Path) -> None:
    """Make `link` point at directory `target` (symlink, else junction on Windows)."""
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        if sys.platform != "win32":
            raise
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                              capture_output=True)
        if made.returncode != 0:
            pytest.skip(f"cannot create a directory link here ({exc})")


def link_file(link: Path, target: Path) -> None:
    """Make `link` a symlink to file `target`, or skip when the host cannot."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"file symlinks need a privilege this host lacks ({exc})")
