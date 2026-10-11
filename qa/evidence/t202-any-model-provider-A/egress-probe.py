import os, socket, sys
os.environ["LITELLM_MODE"]="PRODUCTION"; os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]="True"
hits=[]
def gai(host,*a,**k):
    hits.append(("dns",host)); raise OSError("blocked dns")
def conn(self,addr):
    hits.append(("connect",addr)); raise OSError("blocked connect")
socket.getaddrinfo=gai; socket.socket.connect=conn; socket.socket.connect_ex=lambda s,a:(hits.append(("connect_ex",a)) or 1)
import litellm
for m in ("openai/gpt-4o","anthropic/claude-sonnet-4-5"):
    try:
        r=litellm.completion(model=m,messages=[{"role":"user","content":"hi"}],mock_response='{"a":1}',num_retries=0,api_key="k-test",drop_params=True)
        print(m,"ok",r.choices[0].message.content, r.usage)
    except Exception as e:
        print(m,"EXC",type(e).__name__,str(e)[:150])
import time; time.sleep(3)
print("HITS",hits)
