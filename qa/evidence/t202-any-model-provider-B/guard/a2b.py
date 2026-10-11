import unicodedata
from h import run, outcome, where_leaked
s = "p\u00e4ssw\u00f6rd-9"
nfd = unicodedata.normalize("NFD", s)
r = run(None, "Grade: " + nfd, secrets=[s]); print("NFD spelling:", outcome(r), nfd.encode("unicode_escape"))
s2 = "p\u0430ssword-Xk9"   # cyrillic a secret
r = run(None, "Grade: password-Xk9", secrets=[s2]); print("ascii prompt vs cyrillic-a secret:", outcome(r))
