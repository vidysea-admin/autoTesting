import ast,sys,glob,os
H=sys.argv[1]
files=sorted(glob.glob(H+"/src/autotester/agents/*.py"))+[H+"/src/autotester/schema/agent_layer.py",H+"/tests/test_agent_read_only.py",H+"/tests/test_agent_tools.py"]
for f in files:
    src=open(f,encoding="utf-8").read(); t=ast.parse(src)
    n=len(src.splitlines()); fl=[]
    for x in ast.walk(t):
        if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)):
            fl.append((x.end_lineno-x.lineno+1,x.name,x.lineno))
    fl.sort(reverse=True)
    big=[a for a in fl if a[0]>50]
    print(os.path.relpath(f,H),"lines",n,"OVER300" if n>300 else "ok","docstring",bool(ast.get_docstring(t)),"longest",fl[0] if fl else None,"over50",big)
