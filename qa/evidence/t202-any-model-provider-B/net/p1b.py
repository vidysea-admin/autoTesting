import os, threading
os.environ["LITELLM_MODE"]="PRODUCTION"; os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]="True"
import litellm, asyncio
print(threading.enumerate())
