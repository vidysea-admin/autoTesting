import tempfile, zipfile
from pathlib import Path
from zip_fixtures import make_store, build_zip, video
import autotester.sources.zip_intake as zi
from autotester.sources.zip_names import UnsafePath

def fresh():
    d = Path(tempfile.mkdtemp()); st = make_store(d)
    a = build_zip(d/"h.zip", [("a.mp4", video("a")), ("b.mp4", video("b"))])
    return d, st, a

def left(d, st):
    stage = [p for p in (d/".work").rglob("*") if p.is_file()] if (d/".work").exists() else []
    return len(stage), len(st.list_sources())

def attempt(label, patch_target, attr, exc):
    d, st, a = fresh()
    orig = getattr(patch_target, attr)
    def boom(*args, **kw): raise exc
    setattr(patch_target, attr, boom)
    try:
        r = zi.expand_zip(st, a, max_file_bytes=1<<20)
        print(f"{label}: RETURNED {r.status.value}  (staged files, rows)={left(d, st)}")
    except BaseException as e:
        print(f"{label}: propagated {type(e).__name__}  (staged files, rows)={left(d, st)}")
    finally:
        setattr(patch_target, attr, orig)

attempt("ZipFile ctor KeyboardInterrupt", zipfile, "ZipFile", KeyboardInterrupt())
attempt("ZipFile ctor SystemExit", zipfile, "ZipFile", SystemExit(3))
attempt("ZipFile ctor MemoryError", zipfile, "ZipFile", MemoryError())
attempt("ZipExtFile.read KeyboardInterrupt", zipfile.ZipExtFile, "read", KeyboardInterrupt())
attempt("ZipExtFile.read SystemExit", zipfile.ZipExtFile, "read", SystemExit(3))
attempt("ZipExtFile.read MemoryError", zipfile.ZipExtFile, "read", MemoryError())
attempt("zf.open ValueError (member)", zipfile.ZipFile, "open", ValueError("x"))
attempt("OUR commit_video RuntimeError", zi, "commit_video", RuntimeError("our bug"))
attempt("OUR copy_bounded ValueError", zi, "copy_bounded", ValueError("our bug"))
attempt("OUR ensure_inside UnsafePath", zi, "ensure_inside", UnsafePath("escapes"))
attempt("OUR _classify TypeError", zi, "_classify", TypeError("our bug"))
