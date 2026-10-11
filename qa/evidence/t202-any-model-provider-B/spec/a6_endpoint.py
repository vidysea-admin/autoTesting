import sys, os, shutil, socket, pathlib, json
WT = "D:/autoTesting/.worktrees/t202-any-model-provider"
sys.path.insert(0, WT + "/src"); sys.path.insert(0, WT + "/tests")
HERE = pathlib.Path(__file__).parent
ROOT = HERE / "root_ep"; shutil.rmtree(ROOT, ignore_errors=True); ROOT.mkdir()
os.environ["AUTOTESTER_ROOT"] = str(ROOT)
for k in ("AUTOTESTER_MODEL","LITELLM_API_KEY","LITELLM_API_BASE","OLLAMA_BASE_URL","OPENAI_API_KEY","ANTHROPIC_API_KEY","GEMINI_API_KEY","GOOGLE_API_KEY","GROQ_API_KEY"):
    os.environ.pop(k, None)
attempts=[]; _rc=socket.socket.connect
def _r(self,a):
    if isinstance(a, tuple) and a and a[0] in ("127.0.0.1","::1","localhost"): return _rc(self,a)
    attempts.append(a); raise AssertionError(f"NETWORK {a!r}")
socket.socket.connect=_r
from litellm_fake import FakeLiteLLM, reply
from pydantic import BaseModel
class Ans(BaseModel):
    ok: bool
import autotester.providers as P
from autotester.providers.base import ProviderError

def fresh(responses, **kw):
    f = FakeLiteLLM(responses, **kw); sys.modules["litellm"] = f
    os.environ["LITELLM_MODE"]="PRODUCTION"; os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]="True"; return f

print("=== availability / label with userinfo base ===")
fresh([], missing_keys=["OPENAI_API_KEY"])
os.environ["OLLAMA_BASE_URL"] = "http://user:pw-canary@host:11434"
pr = P.get("litellm", model="ollama/llama3")
print("available:", pr.available(), "| reason:", pr.unavailable_reason(), "| label:", pr.label, "| why_unavailable:", P.why_unavailable(pr))
os.environ.pop("OLLAMA_BASE_URL")
os.environ["LITELLM_API_BASE"] = "http://user:pw-canary@host:11434/v1?key=SECRETQ"
pr = P.get("litellm", model="openai/gpt-4o")
print("available (generic base):", pr.available(), "| reason:", pr.unavailable_reason(), "| label:", pr.label, "| repr:", repr(pr)[:120])
# also no base, key missing -> reason
os.environ.pop("LITELLM_API_BASE")
pr = P.get("litellm", model="openai/gpt-4o")
print("no base, key missing -> reason:", pr.unavailable_reason())
print("str(options):", pr.options)

print("\n=== _failure: exception text variants (fake completion raises) ===")
BASE = "http://user:pw-canary@host:11434/?key=SECRETQ"
os.environ["LITELLM_API_BASE"] = BASE
PROMPT = "Please grade this page: " + "".join(chr(65 + (i % 26)) for i in range(200)) + " END"
variants = {
 "full base in text": f"ConnectError to {BASE}api/chat",
 "base minus scheme (userinfo kept)": "ConnectError to user:pw-canary@host:11434/api/chat",
 "userinfo only": "401 Unauthorized for user pw-canary",
 "query token only": "404 http://host:11434/api/chat?key=SECRETQ not found",
 "host-only": "ConnectError: host:11434 refused",
 "percent-encoded base": "ConnectError to http%3A//user%3Apw-canary%40host:11434",
 "uppercase host": "ConnectError to http://user:pw-canary@HOST:11434/api",
 "prompt head (first 30)": f"bad request: {PROMPT[:30]}",
 "prompt middle (chars 60-110)": f"bad request: messages[0].content: {PROMPT[60:110]}",
 "prompt tail": f"bad request ... {PROMPT[-40:]}",
 "301 chars": "x"*301,
}
for name, text in variants.items():
    f = fresh([RuntimeError(text)])
    pr = P.get("litellm", model="ollama/llama3")
    try:
        pr.judge(PROMPT, Ans); print(f"[{name}] no error?!")
    except ProviderError as e:
        msg = str(e)
        leaked = [t for t in ("pw-canary", "SECRETQ", "user:pw", PROMPT[60:110], PROMPT[-40:]) if t in msg]
        print(f"[{name}] -> {msg[:200]!r}  LEAKED={leaked}")
    except Exception as e:
        print(f"[{name}] !! {type(e).__name__}: {e}")

print("\n=== exported-only vendor key not in the 5 named (GROQ_API_KEY) echoed by exception ===")
os.environ.pop("LITELLM_API_BASE"); os.environ["LITELLM_API_KEY"]="irrelevant-key-1234"
os.environ["GROQ_API_KEY"] = "gsk_live_EXPORTEDONLY_9f8e7d"
fresh([RuntimeError("Invalid API Key: gsk_live_EXPORTEDONLY_9f8e7d")])
pr = P.get("litellm", model="groq/llama3")
try: pr.judge("hello", Ans)
except ProviderError as e: print("->", str(e)[:200], "| LEAKED:", "EXPORTEDONLY" in str(e))
# same with named key
os.environ["OPENAI_API_KEY"] = "sk-live-NAMEDKEY-1111"
fresh([RuntimeError("Invalid API Key: sk-live-NAMEDKEY-1111")])
pr = P.get("litellm", model="openai/gpt-4o")
try: pr.judge("hello", Ans)
except ProviderError as e: print("named key ->", str(e)[:200], "| LEAKED:", "NAMEDKEY" in str(e))
print("network attempts:", attempts)
