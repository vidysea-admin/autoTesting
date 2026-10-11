"""a1: does the guard refuse various spellings of a .env secret in the prompt?"""
import base64, binascii, html, json, urllib.parse
from h import run, outcome, where_leaked

S = "Zq7!kP2x9Lm4"   # 12 chars
ENV = f"MY_SECRET={S}\n"
PRE = "Please grade this test run. "
cases = {
    "plain": PRE + S,
    "percent-encoded": PRE + urllib.parse.quote(S, safe=""),
    "json-escaped (\\u0021)": PRE + S.replace("!", "\\u0021"),
    "base64": PRE + base64.b64encode(S.encode()).decode(),
    "base64 urlsafe nopad": PRE + base64.urlsafe_b64encode(S.encode()).decode().rstrip("="),
    "hex": PRE + S.encode().hex(),
    "html entity": PRE + "".join(f"&#{ord(c)};" for c in S),
    "reversed": PRE + S[::-1],
    "case-changed": PRE + S.upper(),
    "spaced": PRE + " ".join(S),
    "dot-separated": PRE + ".".join(S),
    "hash-separated (#)": PRE + "#".join(S),
    "dollar-separated ($)": PRE + "$".join(S),
    "at-separated (@)": PRE + "@".join(S),
    "bullet-separated (U+2022)": PRE + "•".join(S),
    "digit-inserted": PRE + "0".join(S),
    "cyrillic k homoglyph": PRE + "Zq7!кP2x9Lm4",   # к U+043A not in table
    "half only (first 6)": PRE + S[:6],
    "half only (last 6)": PRE + S[6:],
}
for name, prompt in cases.items():
    r = run(ENV, prompt)
    print(f"{name:32} {outcome(r):22} leak={where_leaked(r, S)}")

# split across two message parts: can only happen via images? parts come from image_url_parts: text part + images.
# Split across user prompt and assistant repair message (strategy json -> repair flow):
print("--- repair-flow split (json strategy, bad first reply carries 2nd half) ---")
first_half, second_half = S[:6], S[6:]
r = run(ENV, PRE + first_half, strategy="json",
        responses=[__import__("h").reply(second_half), __import__("h").reply('{"verdict":"x"}')])
print("repair split:", outcome(r), "calls=", len(r["fake"].calls), "exc=", r["exc"])
for i, c in enumerate(r["fake"].calls):
    print("  call", i, "msgs=", [m["content"][:80] if isinstance(m["content"], str) else "parts" for m in c["messages"]])
