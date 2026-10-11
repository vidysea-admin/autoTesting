import os, sys
import guard; guard.install()
for k in ("LITELLM_MODE","LITELLM_LOCAL_MODEL_COST_MAP"): os.environ.pop(k,None)
from autotester.providers.litellm_provider import _load_litellm
lit=_load_litellm()
msgs=[{"role":"user","content":[{"type":"text","text":"hi there"},{"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="}}]}]
for model in ("openai/gpt-4o","ollama/llama3","gemini/gemini-2.5-pro","anthropic/claude-sonnet-4","meta-llama/Llama-3-8b","mistral/mistral-large-latest","cohere/command-r","unknown/foo"):
    n=len(guard.ATT)
    try: print(model,"token_counter ->",lit.token_counter(model=model,messages=msgs))
    except Exception as e: print(model,"EXC",type(e).__name__,str(e)[:120])
    print("   new attempts:",[(a[0],a[1]) for a in guard.ATT[n:]])
n=len(guard.ATT)
try: print(lit.litellm_core_utils.token_counter.get_image_dimensions("https://example.invalid/x.png"))
except Exception as e: print("get_image_dimensions http EXC",type(e).__name__,str(e)[:100])
print("   new attempts:",[(a[0],a[1]) for a in guard.ATT[n:]])
print("TIKTOKEN_CACHE_DIR",os.environ.get("TIKTOKEN_CACHE_DIR"))
