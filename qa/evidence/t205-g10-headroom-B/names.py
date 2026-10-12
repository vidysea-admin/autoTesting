import os, sys, tempfile
from pathlib import Path
from autotester.core.safe_names import safe_name, safe_slug, encode_slot_key, UnsafeName
from autotester.core.paths import team_path

BS = chr(92)
names = ["..", ".", "", "a/b", "a" + BS + "b", "C:", "C:x", "c:" + BS + "x", "/etc/x", BS + BS + "srv" + BS + "sh",
         "a\x00b", "CON", "con", "nul", "NUL.txt", "com1", "COM¹", "lpt³", "CONIN$", "CONOUT$", "CLOCK$",
         "a.", "a ", "a. ", " a", "a:b", "nul:", "con:", "a:$DATA", "a<b", "a>b", 'a"b', "a|b", "a?b", "a*b",
         "x" * 121, "x" * 120,
         "a∕b", "a／b", "a∖b", "a＼b", "a․․", "․․", "a．", "..​", ".​.",
         "a\n", "a\r", "\x7f", "a‮b", "~1", "PROGRA~1", "a.lnk", "...", "con.", "aux.x.y", "Prn"]
for n in names:
    try:
        safe_name(n); r = "ACCEPTED"
    except UnsafeName:
        r = "refused"
    print(ascii(n)[:40].ljust(42), r)
print("--slot keys")
for k in ["demo:fixed:2026-10-11T09:30Z", "..", "a/b", "con", "CON:x", "a.", "x" * 200, "a b", "é"]:
    try:
        print(ascii(k)[:40], "->", encode_slot_key(k)[:60])
    except UnsafeName:
        print(ascii(k)[:40], "refused")
print("--slug")
for s in ["demo", "demo\n", "Demo", "a" * 300, "con", "nul", "a.b"]:
    try:
        safe_slug(s); print(ascii(s)[:30], "ACCEPTED")
    except UnsafeName:
        print(ascii(s)[:30], "refused")
print("--team_path zero parts:", team_path(root=Path("R")))
