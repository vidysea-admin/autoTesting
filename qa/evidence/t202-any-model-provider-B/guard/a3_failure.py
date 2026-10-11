"""a3: the vendor-exception path (_failure). What reaches ProviderError text / chain?"""
import base64, json, urllib.parse
from h import run, outcome, where_leaked, reply

S = "Zq7!kP2x9Lm4"
ENV = f"MY_SECRET={S}\n"
KEY = "sk-EndpointKey-AbC123xyz"
BASE = "https://Inference.Example.Com/v1"
ENDPT = {"LITELLM_API_KEY": KEY, "LITELLM_API_BASE": BASE}
PROMPT = "Grade this: " + "The login page shows the dashboard after the user signs in with the form. " * 3 + "TAIL-MARKER-XYZ"


def msg(r):
    return str(r["exc"]) if r["exc"] else "(no exc)"


def attempt(name, exc_text, *, prompt=PROMPT, env=ENV, needle=None, endpoint=ENDPT, secrets=None):
    r = run(env, prompt, responses=[RuntimeError(exc_text)], endpoint=endpoint, secrets=secrets)
    m = msg(r)
    # the credential value / marker is in the ProviderError message?
    shown = (needle or "") and needle in m
    print(f"{name:46} calls={len(r['fake'].calls)} needle_in_msg={shown} msg={m[:140]!r}")
    return r


print("== secret value in vendor exception ==")
attempt("exact secret", f"auth failed for {S}", needle=S)
attempt("secret lowercased", f"auth failed for {S.lower()}", needle=S.lower())
attempt("secret percent-encoded", f"GET /x?key={urllib.parse.quote(S, safe='')}", needle=urllib.parse.quote(S, safe=""))
attempt("secret base64", f"Authorization: Basic {base64.b64encode(S.encode()).decode()}", needle=base64.b64encode(S.encode()).decode())
attempt("secret json-escaped (\\u0021)", f'{{"bad":"{S.replace("!", chr(92)+"u0021")}"}}', needle="Zq7")
attempt("secret reversed", f"bad {S[::-1]}", needle=S[::-1])
attempt("secret split by space", f"bad {' '.join(S)}", needle="Z q 7")
attempt("secret split (first 6 / last 6)", f"bad {S[:6]} ... {S[6:]}", needle=S[:6])
attempt("secret html entities", "bad " + "".join(f"&#{ord(c)};" for c in S), needle="&#90;")
print("== endpoint api_key / api_base in vendor exception ==")
attempt("api_key exact", f"bad key {KEY}", needle=KEY)
attempt("api_key lowercased", f"bad key {KEY.lower()}", needle=KEY.lower())
attempt("api_key percent-encoded", "bad key " + urllib.parse.quote(KEY, safe=""), needle="EndpointKey")
attempt("api_key base64", "Bearer-b64 " + base64.b64encode(KEY.encode()).decode(), needle=base64.b64encode(KEY.encode()).decode())
attempt("api_key last 12 chars only", f"bad key ...{KEY[-12:]}", needle=KEY[-12:])
attempt("api_base exact", f"connect to {BASE}", needle=BASE)
attempt("api_base lowercased host", "connect to https://inference.example.com/v1/chat/completions", needle="inference.example.com")
attempt("api_base host only", "connect to Inference.Example.Com:443", needle="Inference.Example.Com")
print("== prompt echo in vendor exception (LL8 'message does not contain the prompt') ==")
attempt("echo prompt first 30 chars", f"bad request: {PROMPT[:30]}", needle=PROMPT[:30])
attempt("echo prompt chars 31..120", f"bad request: {PROMPT[31:120]}", needle=PROMPT[40:100])
attempt("echo prompt tail", f"bad request: ...{PROMPT[-60:]}", needle="TAIL-MARKER-XYZ")
attempt("echo prompt JSON-escaped (newline in first 30)", "bad request: " + json.dumps("Line one\nLine two is here ok")[1:-1],
        prompt="Line one\nLine two is here ok and more text follows after", needle="Line two is here ok")
attempt("echo prompt with quotes JSON-escaped", 'bad: {"content": "' + json.dumps('He said "go now" to the user and left')[1:-1] + '"}',
        prompt='He said "go now" to the user and left', needle="go now")
attempt("echo prompt, 1 space collapsed", "bad request: " + " ".join(PROMPT[:80].split()), needle="The login page shows")
attempt("echo prompt 300-char limit boundary (299)", "x" * 10 + PROMPT[40:330], needle="TAIL")
long_exc = "bad: " + PROMPT[40:] * 3
r = attempt("long exception 301+ chars with prompt echo", long_exc, needle="TAIL")
print("== exceptions that carry nested cause/context ==")
r = run(ENV, PROMPT, responses=[RuntimeError(f"auth {S} and {PROMPT[:30]}")], endpoint=ENDPT)
e = r["exc"]
print("str:", str(e))
print("__cause__:", e.__cause__, "| __suppress_context__:", e.__suppress_context__, "| __context__ str:", str(e.__context__)[:90])
print("leak places:", where_leaked(r, S), " + (only programmatic __context__ shows):")
print("also: ProviderError.__traceback__ frames keep locals: ", end="")
import traceback
tb = e.__traceback__
found = False
while tb:
    for k, v in tb.tb_frame.f_locals.items():
        if isinstance(v, str) and S in v:
            found = True; print(f"frame {tb.tb_frame.f_code.co_name}.{k}", end="; ")
    tb = tb.tb_next
print("found" if found else "none")
