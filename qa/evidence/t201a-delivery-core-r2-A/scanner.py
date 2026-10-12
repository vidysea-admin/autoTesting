import sys, ast
from pathlib import Path
head, base = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(head/"tests"))
import autotester; print(autotester.__file__)
from advice_scan import unresolved_in, unresolved_in_source, advice_in_source
src = head/"src"/"autotester"
u = unresolved_in_source(src); print("head unresolved_in_source:", u)
assert u == []
# every f-string / .format in delivery dir
n=0
for p in sorted((src/"delivery").glob("*.py"))+[src/"schema"/"delivery.py"]:
    t = ast.parse(p.read_text("utf-8"))
    for node in ast.walk(t):
        if isinstance(node, ast.JoinedStr):
            n+=1
            names=[v.value.id for v in node.values if isinstance(v, ast.FormattedValue) and isinstance(v.value, ast.Name)]
            print(f"fstring {p.name}:{node.lineno} names={names}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr=="format":
            print("format call", p.name, node.lineno)
    r = unresolved_in(p.read_text("utf-8"))
    print(p.name, "unresolved_in ->", r); assert r == []
print("fstrings in delivery files:", n)
old = (base/"src/autotester/delivery/inbox.py").read_text("utf-8")
print("old inbox.py unresolved_in ->", unresolved_in(old)); assert unresolved_in(old)
bad = 'import re\nCH = "|".join(["a","b"])\nCHANNELS = "|".join(re.escape(c) for c in ["a","b"])\ndef f(x):\n    return re.compile(f"(?:{CHANNELS})__{x}")\n'
print("synthetic bad ->", unresolved_in(bad)); assert unresolved_in(bad)
good = bad.replace('f"(?:{CHANNELS})__{x}"', '"(?:" + CHANNELS + ")__" + x')
print("synthetic concatenation ->", unresolved_in(good)); assert not unresolved_in(good)
print("SCANNER OK; advice sites at head:", len(advice_in_source(src)))
