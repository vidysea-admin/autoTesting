import sys
f, old, new = sys.argv[1], sys.argv[2].encode().decode('unicode_escape'), sys.argv[3].encode().decode('unicode_escape')
s = open(f, newline='').read()
nl = '\r\n' if '\r\n' in s else '\n'
old, new = old.replace('\n', nl), new.replace('\n', nl)
assert s.count(old) == 1, (s.count(old), old)
open(f, 'w', newline='').write(s.replace(old, new))
