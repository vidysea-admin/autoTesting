import os,sys
os.environ["AUTOTESTER_APPROVAL_KEY"]="x"
from pathlib import Path
from autotester.core.redact import assert_no_raw_secrets
CA="CANARY_ALPHA_0xDEADBEEF_FAKE"
def bare(t):
    try: assert_no_raw_secrets(t,[CA]); return "pass"
    except ValueError: return "CAUGHT"
vs={
 "zw-joined (U+200B)": "\u200b".join(CA),
 "cyrillic A/E upper": CA.replace("A","\u0410").replace("E","\u0415"),
 "cyrillic lower a/e/o/c (only the lowercase-mapped set)": CA.lower().replace("a","\u0430").replace("e","\u0435").replace("o","\u043e"),
 "soft hyphen between chars": "\u00ad".join(CA),
 "combining acute after each char": "".join(c+"\u0301" for c in CA),
 "fullwidth": "".join(chr(ord(c)+0xFEE0) if c.isalnum() and ord(c)<128 else c for c in CA),
 "space-split halves": CA[:14]+" "+CA[14:],
 "newline-split halves": CA[:14]+"\n"+CA[14:],
 "interleaved letter x every char": "x".join(CA),
}
for k,v in vs.items():
    print(f"{k:55} bare={bare(v):7} reprgate={bare(f'run_case '+repr({'case_id': v}))}")
