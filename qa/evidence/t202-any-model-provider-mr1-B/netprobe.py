import socket, sys, os, json
attempts = []
_c = socket.socket.connect
def bad_connect(self, addr, *a, **k):
    h = addr[0] if isinstance(addr, tuple) else str(addr)
    attempts.append(("connect", str(addr))); raise OSError("blocked by checker")
socket.socket.connect = bad_connect
_g = socket.getaddrinfo
def bad_gai(host, *a, **k):
    if host in ("127.0.0.1", "::1", "localhost", None) and False:
        return _g(host, *a, **k)
    attempts.append(("dns", str(host))); raise OSError("blocked by checker")
socket.getaddrinfo = bad_gai
out = {}
import autotester, autotester.providers as P
out["file"] = autotester.__file__; os.environ.pop("OPENAI_API_KEY", None)
out["litellm_after_providers_import"] = "litellm" in sys.modules
import autotester.cli
out["litellm_after_cli_import"] = "litellm" in sys.modules
os.environ.pop("AUTOTESTER_MODEL", None)
prov = P.get("litellm", model="ollama/llama3")
out["label"] = prov.label
out["litellm_after_construct"] = "litellm" in sys.modules
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9"
out["available_with_base"] = prov.available()
out["litellm_after_available"] = "litellm" in sys.modules
out["unavail_reason_via_provider"] = P.get("litellm", model="openai/gpt-4o").unavailable_reason()
import litellm
out["litellm_version"] = __import__("importlib.metadata").metadata.version("litellm")
out["telemetry_attr"] = repr(getattr(litellm, "telemetry", "ABSENT"))
for n in ("callbacks","success_callback","failure_callback","_async_success_callback","_async_failure_callback","input_callback"):
    out["cb_"+n] = repr(getattr(litellm, n, "ABSENT"))
p2 = P.get("litellm", model="openai/gpt-4o")
os.environ.pop("OPENAI_API_KEY", None); os.environ.pop("LITELLM_API_BASE", None); os.environ.pop("LITELLM_API_KEY", None)
out["unavail_reason_nokey"] = p2.unavailable_reason()
out["mode"] = os.environ.get("LITELLM_MODE"); out["costmap"] = os.environ.get("LITELLM_LOCAL_MODEL_COST_MAP")
out["attempts"] = attempts
out["threads"] = __import__("threading").active_count()
print(json.dumps(out, indent=1))
