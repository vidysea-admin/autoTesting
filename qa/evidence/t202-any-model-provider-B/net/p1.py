import os, sys, threading, importlib.metadata as m
import guard; guard.install()
mode = sys.argv[1]
if mode == "flags":
    os.environ["LITELLM_MODE"]="PRODUCTION"; os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]="True"
else:
    os.environ.pop("LITELLM_MODE",None); os.environ.pop("LITELLM_LOCAL_MODEL_COST_MAP",None)
print("litellm", m.version("litellm"))
before = {t.name for t in threading.enumerate()}
import litellm
guard.report("after import")
print("threads new:", [t.name for t in threading.enumerate() if t.name not in before])
print("hasattr telemetry:", hasattr(litellm,"telemetry"))
for n in ["success_callback","failure_callback","callbacks","_async_success_callback","_async_failure_callback","input_callback","service_callback"]:
    print(n, getattr(litellm,n,"<missing>"))
print("TIKTOKEN_CACHE_DIR", os.environ.get("TIKTOKEN_CACHE_DIR"))
print("model_cost entries", len(litellm.model_cost), "litellm_mode", litellm.litellm_mode)
print("proxy imported:", [k for k in sys.modules if k.startswith("litellm.proxy")][:5])
if mode == "flags":
    n0=len(guard.ATT)
    for f,a in [(litellm.supports_response_schema,('openai/gpt-4o',)),(litellm.supports_response_schema,('totally/unknown-model',)),(litellm.supports_function_calling,('openai/gpt-4o',)),(litellm.supports_function_calling,('ollama/llama3',)),(litellm.supports_function_calling,('unknown-xyz',))]:
        try: print(f.__name__,a,"->",f(*a))
        except Exception as e: print(f.__name__,a,"EXC",type(e).__name__,str(e)[:100])
    for model in ['gemini/gemini-2.5-pro','openai/gpt-4o','ollama/llama3','totally/unknown-model','anthropic/claude-sonnet-4']:
        try: print("validate_environment",model,"->",litellm.validate_environment(model=model, api_key=None))
        except Exception as e: print("validate_environment",model,"EXC",type(e).__name__,str(e)[:100])
    guard.report("after probes")
    print("threads now:", [t.name for t in threading.enumerate()])
