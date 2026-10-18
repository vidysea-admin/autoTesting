"""Turn a probe's foreign rows into PII-free `LeakEvidence` and store the finding (MP9, MPI1).

One job: the only place a leaked row is looked at. It counts the rows, keeps their column
headers, hashes at most five ids with HMAC-SHA256, templatises the URL and masks the screenshot
BEFORE anything is written. Cell values never leave this function's arguments: nothing is stored,
logged or returned that holds one. The raw screenshot exists only in a temporary directory outside
the run directory; if masking is not possible the screenshot is withheld, never written raw.

The per-project key is derived from a server key, `AUTOTESTER_LEAK_EVIDENCE_KEY`, in the repo-root
`.env` (read through `core/env.py::load_repo_env`, which exports `AUTOTESTER_*` keys); a project
slug is mixed in so one project's hashes cannot be matched against another's. With no key the ids
are withheld (reason `key_missing`) and the count is still recorded.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from autotester.core.env import load_repo_env
from autotester.core.image_privacy import sanitized_images
from autotester.schema.leak_evidence import MAX_HASHED_IDS, LeakEvidence, segment_is_id_like
from autotester.schema.multi_role_finding import FINDING_ID_PATTERN, MultiRoleFinding
from autotester.store.filestore import write_json

LEAK_KEY_ENV = "AUTOTESTER_LEAK_EVIDENCE_KEY"
FINDINGS_DIR = "multi_role_findings"
SCREENSHOT_DIR = "leak"
_CONTEXT = b"autotester/leak-evidence/v1\0"
_log = logging.getLogger(__name__)


class LeakKeyMissing(RuntimeError):
    """The server key is not configured. The message names the key, never a value."""


def project_key(project_slug: str) -> bytes:
    """The HMAC key for one project, derived from the server key. Raises `LeakKeyMissing`."""
    load_repo_env()
    master = os.environ.get(LEAK_KEY_ENV, "")
    if not master:
        raise LeakKeyMissing(LEAK_KEY_ENV)
    return hmac.new(master.encode("utf-8"), _CONTEXT + project_slug.encode("utf-8"),
                    hashlib.sha256).digest()


def hash_id(key: bytes, raw_id: object) -> str:
    """HMAC-SHA256 hex of one id under `key`."""
    return hmac.new(key, str(raw_id).encode("utf-8"), hashlib.sha256).hexdigest()


def hashed_ids(project_slug: str, rows: Sequence[Mapping[str, object]],
               id_field: str) -> tuple[list[str], str | None]:
    """Hashes of the first distinct ids (at most five), or `([], "key_missing")`."""
    raw = list(dict.fromkeys(
        str(row[id_field]) for row in rows if row.get(id_field) is not None))[:MAX_HASHED_IDS]
    try:
        key = project_key(project_slug)
    except LeakKeyMissing:
        return [], "key_missing"
    return [hash_id(key, value) for value in raw], None


def _safe_key(key: str) -> str:
    plain = key.replace("-", "").replace("_", "").replace(".", "")
    return key if plain.isalpha() and len(key) <= 40 else "{key}"


def templatise_url(url: str) -> str:
    """Replace ids and query values with placeholders; drop userinfo and fragment."""
    parts = urlsplit(url)
    host = (parts.hostname or "") + (f":{parts.port}" if parts.port else "")
    prefix = f"{parts.scheme}://{host}" if parts.scheme and host else ""
    path = "/".join("{id}" if segment_is_id_like(seg) else seg for seg in parts.path.split("/"))
    pairs = [pair.partition("=") for pair in parts.query.split("&") if pair]
    query = "&".join(f"{_safe_key(k)}={{value}}" if sep else _safe_key(k) for k, sep, _ in pairs)
    return prefix + path + (f"?{query}" if query else "")


def store_masked_screenshot(png: bytes, dest: Path) -> tuple[Path | None, str | None]:
    """Mask `png` with `core/image_privacy` and write only the masked copy to `dest`.

    Returns `(dest, None)`, or `(None, <fixed reason code>)` when masking fails: the raw image is
    then written nowhere. The raw bytes touch only a temporary directory that is deleted on exit.
    """
    with TemporaryDirectory(prefix="autotester-leak-") as scratch:
        raw = Path(scratch) / "raw.png"
        raw.write_bytes(png)
        with sanitized_images([raw]) as batch:
            if batch.incomplete or not batch.paths:
                return None, (batch.reasons[0] if batch.reasons else "sanitation_failed")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(batch.paths[0], dest)
    return dest, None


def _screenshot_dest(run_dir: Path, finding_id: str) -> Path:
    """`<run_dir>/leak/<finding_id>.png`; refuse an unsafe slug or a path leaving `run_dir`."""
    if not re.fullmatch(FINDING_ID_PATTERN, finding_id):
        raise ValueError("finding_id must be a lowercase slug")
    dest = run_dir / SCREENSHOT_DIR / f"{finding_id}.png"
    if not dest.resolve().is_relative_to(run_dir.resolve()):
        raise ValueError("the screenshot path must stay inside the run directory")
    return dest


def collect_leak_evidence(*, project_slug: str, run_dir: Path, finding_id: str,
                          rows: Sequence[Mapping[str, object]], id_field: str, url: str,
                          screenshot_png: bytes | None = None) -> LeakEvidence:
    """Reduce the foreign `rows` a probe saw to counts, headers, hashes and a URL template."""
    dest = _screenshot_dest(run_dir, finding_id)
    ids, id_reason = hashed_ids(project_slug, rows, id_field)
    stored: str | None = None
    shot_reason: str | None = None
    if screenshot_png is not None:
        path, shot_reason = store_masked_screenshot(screenshot_png, dest)
        stored = path.relative_to(run_dir).as_posix() if path else None
    headers = list(dict.fromkeys(str(name) for row in rows for name in row))
    return LeakEvidence(
        foreign_row_count=len(rows), field_names=headers, hashed_ids=ids,
        ids_withheld_reason="key_missing" if id_reason else None, screenshot_path=stored,
        screenshot_withheld_reason=shot_reason, url_template=templatise_url(url))


def write_finding(run_dir: Path, finding: MultiRoleFinding) -> Path:
    """Write the finding under the run directory and log one value-free line."""
    path = run_dir / FINDINGS_DIR / f"{finding.finding_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, finding)
    _log.info("multi-role finding %s class=%s count=%d", finding.finding_id,
              finding.finding_class.value, finding.count)
    return path
