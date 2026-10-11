"""a2: odd secret shapes via the `secrets` option (parser-free) -- does the exact value in a prompt refuse?
Also: JSON-escaped / percent-encoded / entity forms for non-ASCII and control-char secrets."""
import json, urllib.parse, html
from h import run, outcome, where_leaked

PRE = "Grade this: "
shapes = {
    "1ch 'x'": "x", "2ch 'q9'": "q9", "3ch 'k#7'": "k#7", "4ch 'Ab3$'": "Ab3$", "7ch 'Ab3$kL9'": "Ab3$kL9",
    "newline mid": "ab\ncd1234", "tab mid": "ab\tcd1234", "CR mid": "ab\rcd1234", "NUL mid": "ab\x00cd1234",
    "trailing newline": "Ab3dE9\n", "leading space": " Ab3dE9x",
    "regex meta '.*'": ".*", "regex '(a|b'": "(a|b", "regex '[x'": "[x", "backslash 'a\\b'": "a\\b",
    "accents": "pässwörd-9", "CJK": "密码密码密码", "emoji": "\U0001F511\U0001F511K9",
    "cyrillic homoglyph a": "pаssword-Xk9",
}
print("== exact value in prompt (via secrets option) ==")
for name, v in shapes.items():
    r = run(None, PRE + "start " + v + " end", secrets=[v])
    print(f"{name:26} exact:{outcome(r):22} leak={where_leaked(r, v)}")

print("== encoded spellings of non-ASCII / control-char secrets ==")
enc = {
    "accents json ensure_ascii": ("pässwörd-9", json.dumps("pässwörd-9")[1:-1]),
    "accents decomposed NFD": ("pässwörd-9", "pässswörd-9".replace("ssss", "sss")),
    "accents percent": ("pässwörd-9", urllib.parse.quote("pässwörd-9")),
    "accents html entity": ("pässwörd-9", html.escape("pässwörd-9").encode("ascii", "xmlcharrefreplace").decode()),
    "CJK json ensure_ascii": ("密码密码密码", json.dumps("密码密码密码")[1:-1]),
    "newline secret json-escaped (\\n)": ("abcd1234\nefgh5678", json.dumps("abcd1234\nefgh5678")[1:-1]),
    "newline secret as space": ("abcd1234\nefgh5678", "abcd1234 efgh5678"),
    "tab secret json-escaped (\\t)": ("abcd1234\tefgh5678", json.dumps("abcd1234\tefgh5678")[1:-1]),
    "quote secret json-escaped": ('ab"cd1234xy', json.dumps('ab"cd1234xy')[1:-1]),
    "backslash secret json-escaped": ("ab\\cd1234xy", json.dumps("ab\\cd1234xy")[1:-1]),
    "NUL secret json-escaped (\\u0000)": ("abcd\x001234xyz", json.dumps("abcd\x001234xyz")[1:-1]),
    "trailing-nl 6ch val, bare": ("Ab3dE9\n", "Ab3dE9 and more"),
    "trailing-nl 8ch val, bare": ("Ab3dE9xY\n", "Ab3dE9xY and more"),
    "leading-space 7ch, bare": (" Ab3dE9x", "Ab3dE9x and more"),
}
for name, (secret, shown) in enc.items():
    r = run(None, PRE + shown, secrets=[secret])
    print(f"{name:36} {outcome(r):22} leak={where_leaked(r, shown) if r['fake'].calls else '-'}")
