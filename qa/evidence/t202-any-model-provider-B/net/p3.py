import os, sys, threading
import guard; guard.install()
for k in ("LITELLM_MODE","LITELLM_LOCAL_MODEL_COST_MAP"): os.environ.pop(k,None)
from autotester.providers.litellm_provider import _load_litellm
lit=_load_litellm()
msgs=[{"role":"user","content":[{"type":"text","text":"hi"},{"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgo="}}]}]
for model in ("openai/gpt-4o","ollama/llama3","gemini/gemini-2.5-pro","anthropic/claude-sonnet-4"):
    try:
        r=lit.completion(model=model,messages=msgs,mock_response="ok",api_key="x",num_retries=0,timeout=2,drop_params=True)
        print(model,"OK",r.choices[0].message.content, r.usage)
    except Exception as e: print(model,"EXC",type(e).__name__,str(e)[:150])
import time; time.sleep(1.5)
nonloop=[a for a in guard.ATT if not a[1].startswith("('127.0.0.1'")]
print("non-loopback attempts:",nonloop, "total", len(guard.ATT))
for a in guard.ATT: print(a[0],a[1])
print("threads:",[t.name for t in threading.enumerate()])
for nme in ["success_callback","failure_callback","callbacks","_async_success_callback","_async_failure_callback","input_callback","service_callback"]:
    print(nme, getattr(lit,nme))
print("TIKTOKEN_CACHE_DIR",os.environ.get("TIKTOKEN_CACHE_DIR"))
