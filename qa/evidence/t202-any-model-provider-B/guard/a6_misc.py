"""a6: unscanned channels (image parts, tools/response_format), exempt config keys, options retention."""
import base64, json, tempfile
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from h import run, outcome, where_leaked, Ans, reply
import h

S = "Zq7!kP2x9Lm4"
PRE = "Grade this: "

print("== image_url data part (non-text parts never scanned) ==")
d = Path(tempfile.mkdtemp(prefix="t202b-img-"))
f = d / "shot.png"
f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"AAAA password field value: " + S.encode() + b" END")
r = run(f"MY_SECRET={S}\n", PRE + "see screenshot", images=[f])
print("  outcome:", outcome(r))
if r["fake"].calls:
    parts = r["fake"].calls[0]["messages"][0]["content"]
    url = [p for p in parts if p["type"] == "image_url"][0]["image_url"]["url"]
    raw = base64.b64decode(url.split(",", 1)[1])
    print("  decoded data-URL contains secret value:", S.encode() in raw)

print("== secret in prompt AND in an attached image-part-only (text part clean) -> CALLED means unscanned ==")

print("== schema carrying a secret in a Field description (tools / response_format are not scanned) ==")
class Leaky(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: str = Field(description=f"use token {S}")
import sys, os, tempfile as tf
tmp = Path(tf.mkdtemp(prefix="t202b-")); (tmp / ".env").write_text(f"MY_SECRET={S}\n")
os.environ["AUTOTESTER_ROOT"] = str(tmp)
fk = h.Fake([reply('{"verdict":"ok"}')]); sys.modules["litellm"] = fk
from autotester.providers.litellm_provider import LiteLLMProvider
LiteLLMProvider(model="openai/gpt-4o").judge(PRE + "x", Leaky)
print("  CALLED with secret in kwargs:", [k for k, v in fk.calls[0].items() if S in json.dumps(v)])
fk = h.Fake([reply('{"verdict":"ok"}')], schema=False, tool=False); sys.modules["litellm"] = fk
try:
    LiteLLMProvider(model="openai/gpt-4o").judge(PRE + "x", Leaky)
    print("  json strategy (instruction is in the TEXT, scanned): CALLED")
except Exception as e:
    print("  json strategy (instruction is in the TEXT, scanned):", type(e).__name__, e)
os.environ.pop("AUTOTESTER_ROOT")

print("== config keys exempt from the guard may carry credentials ==")
for label, env, prompt in [
    ("LITELLM_API_BASE userinfo password", "LITELLM_API_BASE=https://svc:Hunter2-Pw9x@llm.internal.example/v1\n", PRE + "password is Hunter2-Pw9x"),
    ("LITELLM_API_BASE path token", "LITELLM_API_BASE=https://api.example/v2/TOK-8f3a1c9d77e2b4/openai/v1\n", PRE + "see TOK-8f3a1c9d77e2b4"),
    ("OLLAMA_BASE_URL query key", "OLLAMA_BASE_URL=http://h:11434/?key=abcd1234efgh5678\n", PRE + "abcd1234efgh5678"),
    ("AUTOTESTER_MODEL value", "AUTOTESTER_MODEL=openai/gpt-4o\n", PRE + "openai/gpt-4o"),
]:
    r = run(env, prompt); print(f"  {label:36} {outcome(r)}")

print("== secrets option retained in provider.options (serialisable surface?) ==")
r = run(None, PRE + "hi", secrets=[S])
print("  p.options =", r["p"].options)
print("  repr(p) contains secret:", S in repr(r["p"]), "| label:", r["p"].label)
