import socket, json, sys
hosts=json.load(open(sys.argv[1],encoding='utf-8')); out={}
for h in hosts:
    fam = socket.AF_INET6 if h and ":" in h else socket.AF_INET
    s=socket.socket(fam)
    try:
        s.bind((h,0)); out[h]={"kind":"bound","addr":s.getsockname()[0]}
    except socket.gaierror as e: out[h]={"kind":"gaierror","addr":str(e)}
    except OSError as e: out[h]={"kind":"oserror","addr":f"{e.errno} {e}"}
    s.close()
json.dump(out,open(sys.argv[2],'w',encoding='utf-8'),indent=1)
