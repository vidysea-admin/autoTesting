import shutil, sys
from pathlib import Path
W = Path(sys.argv[1])
M = {
 "key":   ("delivery/inbox.py", '''    return "".join("_0" if c == "_" else f"_{c.lower()}" if c.isupper() else c
                   for c in safe_id(value))''', '''    return safe_id(value)'''),
 "match": ("delivery/inbox.py", '''re.escape(key) + r"\.\d+\.json"''', '''re.escape(key) + r"\..*\.json"'''),
 "race":  ("delivery/inbox.py", '''        log.append(key, record)
    except FileExistsError:
        # A second''', '''        log.append(key, record)
    except ZeroDivisionError:
        # A second'''),
 "slash": ("schema/delivery.py", '/(?!/)[A-Za-z0-9._~/-]*', '/[A-Za-z0-9._~/-]*'),
 "port":  ("schema/delivery.py", 'not 1 <= int(match.group(1)) <= 65535', 'False'),
}
for name, (f, old, new) in M.items():
    d = W / f"mut-{name}"
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(W / "copy" / "src", d / "src", ignore=shutil.ignore_patterns("__pycache__"))
    p = d / "src" / "autotester" / f
    s = p.read_text("utf-8")
    assert s.count(old) == 1, (name, s.count(old))
    p.write_text(s.replace(old, new), "utf-8")
    print("mutated", name, f)
