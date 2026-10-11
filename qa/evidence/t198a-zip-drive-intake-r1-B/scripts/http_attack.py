"""Seat B r1: field-cap attacks against the upload route (ASGI level, no network).

usage: python http_attack.py <SRC> <WORK> <out.json> [case-prefix]
"""
import gc
import json
import os
import sys
import tracemalloc
from pathlib import Path

SRC, WORK, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
ONLY = sys.argv[4] if len(sys.argv) > 4 else ""
sys.path.insert(0, str(SRC))
sys.path.insert(0, "D:/autoTesting/.worktrees/t198a-zip-drive-intake/tests")
import autotester  # noqa: E402

assert str(SRC.resolve()) in str(Path(autotester.__file__).resolve())
from asgi_helpers import BOUNDARY, post_stream  # noqa: E402

from autotester.core.paths import ENV_ROOT  # noqa: E402
from autotester.schema.project import Project  # noqa: E402
from autotester.schema.server_settings import ServerSettings  # noqa: E402
from autotester.store.project_store import ProjectStore  # noqa: E402
from autotester.store.server_settings import save_server_settings  # noqa: E402

UPLOAD = "/projects/demo/sources/upload"
B = BOUNDARY.encode()
CH = 64 * 1024
MP4 = b"MP4-b1|" * 700


def part(name, value=b"", filename=None, extra_headers=b""):
    disp = f'Content-Disposition: form-data; name="{name}"'
    if filename is not None:
        disp += f'; filename="{filename}"'
    return b"--" + B + b"\r\n" + disp.encode() + b"\r\n" + extra_headers + b"\r\n" + value + b"\r\n"


TAIL = b"--" + B + b"--\r\n"


def file_part(name="a.mp4", data=MP4):
    return part("recording", data, filename=name)


def slabs(gen, size=CH):
    """regroup an iterator of byte strings into <=size chunks lazily"""
    buf = bytearray()
    for piece in gen:
        buf += piece
        while len(buf) >= size:
            yield bytes(buf[:size])
            del buf[:size]
    if buf:
        yield bytes(buf)


def repeat(unit, count):
    for _ in range(count):
        yield unit


def make_env(tag, limit_mib):
    root = WORK / tag
    root.mkdir(parents=True)
    os.environ[ENV_ROOT] = str(root)
    st = ProjectStore("demo", root)
    st.save_project(Project(slug="demo", name="Demo", base_url="https://demo.test",
                            allowed_domains=["demo.test"]))
    save_server_settings(ServerSettings(max_upload_bytes=limit_mib * 1024 * 1024), root)
    return root, st


def leftovers(root):
    found = []
    for area in ("intake", "drive-fetch", "gws", "uploads"):
        base = root / ".work" / area
        found += [str(p.relative_to(root)) for p in base.rglob("*") if p.is_file()] if base.exists() else []
    return found


def uploads_dirs(root):
    base = root / ".work" / "uploads"
    return [str(p.relative_to(root)) for p in base.rglob("*")] if base.exists() else []


CASES = {}


def case(name, limit_mib=2):
    def deco(fn):
        CASES[name] = (fn, limit_mib)
        return fn
    return deco


# ---- count / total caps
@case("empty-names-x200k-then-file")
def _():
    return slabs(list(repeat(part("", b"v"), 200_000)) and (p for p in [*repeat(part("", b"v"), 200_000), file_part(), TAIL]))


@case("empty-names-endless-no-file", 1)
def _():
    def g():
        n = 0
        while n < 4000 * 1024:
            yield part("", b"v" * 20)
            n += 120
    return slabs(g())


@case("dup-name-label-x20000-then-file")
def _():
    return slabs(p for p in [*repeat(part("label", b"v"), 20_000), file_part(), TAIL])


@case("distinct-names-x9-then-file")
def _():
    return slabs(p for p in [*(part(f"f{i}", b"v") for i in range(9)), file_part(), TAIL])


@case("distinct-names-x8-then-file")
def _():
    return slabs(p for p in [*(part(f"f{i}", b"v") for i in range(8)), file_part(), TAIL])


@case("distinct-names-x9-AFTER-file")
def _():
    return slabs(p for p in [file_part(), *(part(f"f{i}", b"v") for i in range(9)), TAIL])


@case("dup-name-AFTER-file-x20000")
def _():
    return slabs(p for p in [file_part(), *repeat(part("label", b"v"), 20_000), TAIL])


@case("nofilename-recording-parts-x50")
def _():
    return slabs(p for p in [*(part("recording", b"zzz") for _ in range(50)), file_part(), TAIL])


@case("nofilename-recording-parts-x8-then-file-9th-name")
def _():
    return slabs(p for p in [*(part(f"r{i}", b"zzz") for i in range(8)), part("label", b"x"), file_part(), TAIL])


@case("name-7900B-x5-then-file")
def _():
    return slabs(p for p in [*(part(("n%d" % i) + "x" * 7900, b"v") for i in range(5)), file_part(), TAIL])


@case("name-9000B-header-over-cap")
def _():
    return slabs(p for p in [part("x" * 9000, b"v"), file_part(), TAIL])


@case("value-16384-single-then-file")
def _():
    return slabs(p for p in [part("label", b"v" * 16384), file_part(), TAIL])


@case("value-16385-single-then-file")
def _():
    return slabs(p for p in [part("label", b"v" * 16385), file_part(), TAIL])


@case("value-16384-x2-then-file")
def _():
    return slabs(p for p in [part("a", b"v" * 16384), part("b", b"v" * 16384), file_part(), TAIL])


@case("value-16384-and-small-sum-just-over-32K")
def _():
    return slabs(p for p in [part("a", b"v" * 16384), part("b", b"v" * 16368), part("c", b"v"), file_part(), TAIL])


@case("value-just-under-total: 16384 + 16300")
def _():
    return slabs(p for p in [part("a", b"v" * 16384), part("b", b"v" * 16300), file_part(), TAIL])


@case("single-field-endless-value", 1)
def _():
    def g():
        yield b"--" + B + b'\r\nContent-Disposition: form-data; name="label"\r\n\r\n'
        for _ in range(100):
            yield b"v" * CH
    return g()


# ---- header count in one part (not a field-count question: a memory question)
for mb in (4, 8, 16):
    @case(f"headers-distinct-in-one-part-{mb}MiB", 64)
    def _(mb=mb):
        def g():
            yield b"--" + B + b'\r\nContent-Disposition: form-data; name="label"\r\n'
            total, i = 0, 0
            while total < mb * 1024 * 1024:
                h = b"H%d: v\r\n" % i
                total += len(h)
                i += 1
                yield h
            yield b"\r\nx\r\n"
            yield file_part()
            yield TAIL
        return slabs(g())


@case("headers-distinct-in-FILE-part-8MiB", 64)
def _():
    def g():
        yield b"--" + B + b'\r\nContent-Disposition: form-data; name="recording"; filename="a.mp4"\r\n'
        total, i = 0, 0
        while total < 8 * 1024 * 1024:
            h = b"H%d: v\r\n" % i
            total += len(h)
            i += 1
            yield h
        yield b"\r\n" + MP4 + b"\r\n"
        yield TAIL
    return slabs(g())


@case("many-empty-parts-no-headers-8MiB", 64)
def _():
    def g():
        n = 0
        while n < 8 * 1024 * 1024:
            u = b"--" + B + b"\r\n\r\n\r\n"
            n += len(u)
            yield u
        yield file_part()
        yield TAIL
    return slabs(g())


# ---- chunking
@case("one-byte-chunks-valid-with-label")
def _():
    body = b"".join([part("label", b"hello"), file_part(), TAIL])
    return (body[i:i + 1] for i in range(len(body)))


@case("one-byte-chunks-9-fields")
def _():
    body = b"".join([*(part(f"f{i}", b"v") for i in range(9)), file_part(), TAIL])
    return (body[i:i + 1] for i in range(len(body)))


@case("split-boundary-marker-7byte-chunks-valid")
def _():
    body = b"".join([part("label", b"hello"), file_part(), TAIL])
    return (body[i:i + 7] for i in range(0, len(body), 7))


@case("filename-no-content")
def _():
    return slabs(p for p in [part("label", b"x"), part("recording", b"", filename="a.mp4"), TAIL])


@case("distinct-names-x50000-then-file", 8)
def _():
    return slabs(p for p in [*(part(f"f{i}", b"v" * 40) for i in range(50_000)), file_part(), TAIL])


@case("distinct-names-x150000-then-file", 16)
def _():
    return slabs(p for p in [*(part(f"f{i}", b"v" * 40) for i in range(150_000)), file_part(), TAIL])


@case("valid-baseline")
def _():
    return slabs(p for p in [part("label", b"hello"), file_part(), TAIL])


def run(name, gen_fn, limit_mib):
    root, st = make_env(name.replace(":", "_").replace(" ", "_")[:50], limit_mib)
    gen = gen_fn()
    gc.collect()
    tracemalloc.start()
    status = body = served = None
    err = None
    try:
        status, page, sv = post_stream(UPLOAD, gen, host="localhost")
        served = sv.bytes
        body = page.decode("utf-8", "replace")
        import re
        m = re.search(r"<p>(.*?)</p>", body)
        body = m.group(1)[:90] if m else body[:90]
    except BaseException as e:
        err = repr(e)[:200]
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"case": name, "status": status, "msg": body, "served_bytes": served, "peak_mib": round(peak / 1048576, 2),
            "rows": len(st.list_sources()), "leftover_files": leftovers(root), "uploads_dirs": uploads_dirs(root),
            "limit_mib": limit_mib, "err": err}


if __name__ == "__main__":
    res = []
    for n, (fn, lim) in CASES.items():
        if ONLY and not n.startswith(ONLY):
            continue
        r = run(n, fn, lim)
        res.append(r)
        print(r["case"], r["status"], r["msg"], "served", r["served_bytes"], "peak", r["peak_mib"], "rows", r["rows"],
              "left", len(r["leftover_files"]), r["err"] or "", flush=True)
    OUT.write_text(json.dumps(res, indent=1))
