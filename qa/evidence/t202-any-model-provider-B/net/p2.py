import os, sys, threading, asyncio
import guard; guard.install()
for k in ("LITELLM_MODE","LITELLM_LOCAL_MODEL_COST_MAP","LITELLM_API_BASE","LITELLM_API_KEY","OLLAMA_BASE_URL","OPENAI_API_KEY","AUTOTESTER_MODEL"): os.environ.pop(k,None)
from autotester.providers.litellm_provider import LiteLLMProvider
print("litellm in sys.modules before:", "litellm" in sys.modules)
p = LiteLLMProvider(model="openai/gpt-4o")
print("available():", p.available(), "|", p.unavailable_reason())
guard.report("provider.available")
print("env after: MODE=",os.environ.get("LITELLM_MODE"),"MAP=",os.environ.get("LITELLM_LOCAL_MODEL_COST_MAP"))
print("threads:", [t.name for t in threading.enumerate()])
p2 = LiteLLMProvider(model="ollama/llama3"); print("ollama available():", p2.available(), "|", p2.unavailable_reason())
import litellm
print("hasattr telemetry after provider set:", hasattr(litellm,"telemetry"), getattr(litellm,"telemetry",None))
n=len(guard.ATT)
try:
    litellm.completion(model="openai/gpt-4o", messages=[{"role":"user","content":"hi"}], api_base="http://192.0.2.1:9/v1", api_key="x", num_retries=0, timeout=2)
except Exception as e:
    print("completion raised:", type(e).__name__, str(e)[:160].replace("\n"," "))
guard.report("after completion")
print("threads:", [t.name for t in threading.enumerate()])
for nme in ["success_callback","failure_callback","callbacks","_async_success_callback","_async_failure_callback","input_callback","service_callback"]:
    print(nme, getattr(litellm,nme))
print("asyncio loop running thread names / tiktoken env:", os.environ.get("TIKTOKEN_CACHE_DIR"))
print("new litellm modules touching network libs:", [k for k in ("posthog","sentry_sdk","langfuse","prometheus_client","opentelemetry","tiktoken","tokenizers","huggingface_hub") if k in sys.modules])
