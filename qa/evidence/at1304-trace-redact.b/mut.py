import sys
p, a, b = sys.argv[1], sys.argv[2].encode().decode("unicode_escape"), sys.argv[3].encode().decode("unicode_escape")
s = open(p, encoding="utf-8").read(); assert a in s, "anchor missing"; open(p, "w", encoding="utf-8").write(s.replace(a, b))
