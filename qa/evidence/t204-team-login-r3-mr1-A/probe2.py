import os, sys, tempfile, re
arch = open('arch_path.txt').read().strip()
root = tempfile.mkdtemp(prefix='probe2_', dir=os.path.dirname(os.path.abspath(__file__)))
os.environ['AUTOTESTER_ROOT'] = root
for k in list(os.environ):
    if k.startswith('AUTOTESTER_') and k!='AUTOTESTER_ROOT': del os.environ[k]
from autotester.ui.app import app
import autotester; print(autotester.__file__)
from fastapi.testclient import TestClient
def flat(routes):
    for r in routes:
        inner = getattr(r, 'original_router', None)
        if inner is not None: yield from flat(inner.routes)
        else: yield r
pairs=set()
for r in flat(app.routes):
    p=getattr(r,'path',None)
    for m in (getattr(r,'methods',None) or []):
        if m!='HEAD' and p: pairs.add((m,p))
H={'Origin':'http://localhost'}
def client(): return TestClient(app, base_url='http://localhost', follow_redirects=False)
adm=client(); r=adm.post('/auth/signup',data={'email':'a@scratch.test','password':'correct-horse-9','display_name':'a'},headers=H); print('signup1',r.status_code)
u=client(); r=u.post('/auth/signup',data={'email':'b@scratch.test','password':'correct-horse-9','display_name':'b'},headers=H); print('signup2',r.status_code)
open_=[]
for m,p in sorted(pairs):
    if p in ('/auth/login','/auth/signup','/healthz'): continue
    c=re.sub(r'\{[^}:]+(:path)?\}','x',p)
    if p=='/auth/logout': continue
    resp=u.request(m,c,headers=H)
    if p=='/auth/logout': continue
    if p=='/auth/waiting': 
        print('allowed-for-zero-perm', m,p,resp.status_code); continue
    if resp.status_code!=403: open_.append((m,p,resp.status_code))
print('zero-permission account non-403:', open_)
print('GET / ->', u.get('/').status_code, 'waiting', u.get('/auth/waiting').status_code)
r=u.post('/onboard',headers=H); print('POST /onboard', r.status_code, r.text[:200], dict(r.headers))
print(u.cookies)
