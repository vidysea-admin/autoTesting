"""Test helpers for the zip-intake tests (T-198a, team-intake.md TI1-TI6).

Builds hostile and benign archives on any host. A member name is assigned to
`ZipInfo.filename` AFTER construction because `ZipInfo.__init__` rewrites `os.sep`
and cuts at a NUL, which would make the same fixture differ between Windows and
Ubuntu (R65) and hide exactly the names the contract is about.
"""

from __future__ import annotations

import stat
import tempfile
import uuid
import zipfile
from pathlib import Path

from autotester.store.project_store import ProjectStore


def video(tag: str, *, size: int = 4096) -> bytes:
    """Distinct bytes per `tag` (so sha256 differs) that look nothing like an archive."""
    return (f"MP4-{tag}|".encode() * (size // 8 + 1))[:size]


def add_member(archive: zipfile.ZipFile, name: str, data: bytes = b"", *,
               mode: int | None = None, compress: int = zipfile.ZIP_STORED) -> None:
    info = zipfile.ZipInfo("placeholder")
    info.filename = name  # bypass ZipInfo.__init__ normalisation, see module docstring
    info.compress_type = compress
    if mode is not None:
        info.create_system = 3
        info.external_attr = mode << 16
    archive.writestr(info, data)


def build_zip(path: Path, members: list[tuple[str, bytes]], **kwargs) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members:
            add_member(archive, name, data, **kwargs)
    return path


def build_special(path: Path, name: str, mode: int, data: bytes = b"target") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        add_member(archive, name, data, mode=mode)
        add_member(archive, "ok.mp4", video("benign"))
    return path


SPECIAL_MODES = {
    "symlink": stat.S_IFLNK | 0o777,
    "device": stat.S_IFCHR | 0o666,
    "fifo": stat.S_IFIFO | 0o666,
    "socket": stat.S_IFSOCK | 0o666,
}


def flip_data_byte(archive_path: Path, member: str) -> None:
    """Flip one byte in the middle of a STORED member's data so its CRC no longer matches."""
    with zipfile.ZipFile(archive_path) as archive:
        info = archive.getinfo(member)
        start = info.header_offset + 30 + len(info.orig_filename.encode()) + len(info.extra)
        offset = start + info.compress_size // 2
    raw = bytearray(archive_path.read_bytes())
    raw[offset] ^= 0xFF
    archive_path.write_bytes(bytes(raw))


def mark_encrypted(archive_path: Path) -> None:
    """Set the 'encrypted' general-purpose bit on every member (local + central header)."""
    raw = bytearray(archive_path.read_bytes())
    for signature, flag_at in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        position = raw.find(signature)
        while position != -1:
            raw[position + flag_at] |= 0x01
            position = raw.find(signature, position + 4)
    archive_path.write_bytes(bytes(raw))


def make_store(tmp_path: Path, slug: str = "demo") -> ProjectStore:
    store = ProjectStore(slug, root=tmp_path)
    store.paths.dir.mkdir(parents=True, exist_ok=True)
    return store


def plant_sentinels(tmp_path: Path, store: ProjectStore) -> dict[Path, bytes]:
    """Files an escaping member would clobber: above staging, above the project, and at the
    host's temp root. The test later asserts each is byte-identical."""
    spots = [
        tmp_path / "sentinel-root.txt",
        tmp_path / ".work" / "sentinel-work.txt",
        tmp_path / ".work" / "intake" / "sentinel-intake.txt",
        store.paths.dir / "sentinel-project.txt",
        Path(tempfile.gettempdir()) / f"at-sentinel-{uuid.uuid4().hex}.txt",
    ]
    planted: dict[Path, bytes] = {}
    for spot in spots:
        spot.parent.mkdir(parents=True, exist_ok=True)
        content = f"sentinel {spot.name}".encode()
        spot.write_bytes(content)
        planted[spot] = content
    return planted


def files_outside_project_sources(tmp_path: Path, store: ProjectStore) -> set[Path]:
    """Every file under tmp_path except the project's registered output."""
    sources = store.paths.sources_dir
    allowed_index = store.paths.sources_index
    found = {p for p in tmp_path.rglob("*") if p.is_file()}
    return {p for p in found if sources not in p.parents and p != allowed_index}
