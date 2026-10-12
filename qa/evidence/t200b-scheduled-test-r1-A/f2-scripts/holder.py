import sys, time, os
from pathlib import Path
mode, target, ready, stop = sys.argv[1:5]
if mode == "default":
    fh = open(target, "rb")          # Python default: no FILE_SHARE_DELETE
elif mode == "osopen":
    fd = os.open(target, os.O_RDONLY)
elif mode == "append":
    fd = os.open(target, os.O_APPEND | os.O_WRONLY)
elif mode == "sharedelete":
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.restype = wintypes.HANDLE
    h = k.CreateFileW(target, 0x80000000, 7, None, 3, 0x80, None)  # READ, share R|W|DELETE, OPEN_EXISTING
    assert h not in (None, wintypes.HANDLE(-1).value), ctypes.get_last_error()
elif mode == "reader":
    sys.path.insert(0, str(Path(__file__).parent))
    from autotester.stages.schedule_store import read_records
    Path(ready).write_text("1")
    errs = {}
    n = 0
    while not Path(stop).exists():
        try: read_records(Path(target)); n += 1
        except Exception as e: errs[type(e).__name__] = errs.get(type(e).__name__, 0) + 1
    Path(ready + ".errs").write_text(f"reads_ok={n} errors={errs}")
    sys.exit(0)
Path(ready).write_text("1")
while not Path(stop).exists(): time.sleep(0.05)
