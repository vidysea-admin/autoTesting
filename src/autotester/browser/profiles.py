"""Establish a logged-out entry profile before any browser opens."""

import contextlib
import shutil
from pathlib import Path


def wipe_entry_profile(profile: Path) -> None:
    """Remove the entry profile and positively establish it is gone (RU5, C12).
    An already-absent directory is success. A failed removal, a directory still
    present, or an existence check that itself raises all propagate as `OSError`
    (never `ignore_errors`, never `os.path.lexists`, which reads an error as
    'absent'), so the caller never starts a browser on a logged-in profile."""
    try:
        with contextlib.suppress(FileNotFoundError):
            shutil.rmtree(profile)
        present = profile.exists()
    except OSError as exc:
        cause = f"{type(exc).__name__}: {exc}"
        raise OSError(f"entry profile not removed: {profile} ({cause})") from exc
    if present:
        raise OSError(f"entry profile not removed: {profile} (still present after removal)")

