import sys
from pathlib import Path
W = Path(r"D:/autoTesting/.worktrees/t197-video-pointers")
sys.path[:0] = [str(W/"src")]
from autotester.stages.video_pointers import *
from autotester.stages import video_pointers as vp
D=600.0
def r(label, text):
    p = parse_pointers(text, D)
    ident = len(p.parsed)+len(p.errors)==p.non_blank_lines
    print(f"{label:46} parsed={len(p.parsed):4} errors={len(p.errors):4} nonblank={p.non_blank_lines:5} identity={ident}", (p.errors[0].reason[:60] if p.errors else ""))
r("100 lines", "".join(f"0:{n%60:02d} | n{n}\n" for n in range(100)))
r("101 lines", "".join(f"0:{n%60:02d} | n{n}\n" for n in range(101)))
r("101 lines CRLF", "".join(f"0:{n%60:02d} | n{n}\r\n" for n in range(101)))
r("note 500", "1:00 | "+"x"*500)
r("note 501", "1:00 | "+"x"*501)
r("note 500 multibyte(3B)", "1:00 | "+"語"*500)
r("note 501 multibyte", "1:00 | "+"語"*501)
r("free 500", "x"*500)
r("free 501", "x"*501)
r("note 500 + surrounding spaces", "1:00 |   "+"x"*500+"   ")
r("empty note after pipe", "1:00 | ")
r("BOM + 1 line", "\ufeff1:00 | hi")
r("BOM + CRLF", "\ufeff1:00\r\n2:00 | a\r\n")
# file size exact
line = "1:00 | " + "x"*400 + "\n"
n = 32768 // len(line)
body = line*n
pad = 32768 - len(body.encode())
body2 = body + ("x"*(pad-1)+"\n" if pad>1 else "")
print("body bytes", len(body2.encode()))
r("exactly 32768 bytes (many lines)", body2)
r("32769 bytes", body2+"y")
r("32768 bytes incl BOM(3B) -> 32771", "\ufeff"+body2)
r("40KB single line", "1:00 | "+"x"*40000)
r("32768 chars single valid-ish line", "1:00 | "+"x"*(32768-7))
r("multibyte file 10923 chars *3B = 32769", "語"*10923)
r("multibyte file 10922 chars -> 32766B", "1:00 | " + "語"*0 + "x"*0)
print("oversize in CLI uses stat bytes; parser uses len(text.encode) -> consistent?")
