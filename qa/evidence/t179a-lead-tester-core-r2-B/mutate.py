import sys
f, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(f, encoding="utf8").read()
assert s.count(old) == 1, (s.count(old), old)
open(f, "w", encoding="utf8").write(s.replace(old, new))
print("mutated", f)
