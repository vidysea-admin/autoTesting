import re, sys, pickle
from common import *
port = 22102
p, root = start("run2", port)
print("pid", p.pid)
s, ck, _ = login(port, *ADMIN); print("admin login", s, ck)
s, hd, d = req(port, "GET", "/admin/groups", cookie=ck); print(s); html = d.decode()
print(re.findall(r"/admin/groups/(\d+)[^<]*>([^<]*)", html))
s, hd, d = req(port, "GET", "/admin/users", cookie=ck); html = d.decode(); print(s)
print(re.findall(r"/admin/users/(\d+)/(\w+)", html)[:6]); print(re.findall(r"name='group_id' value='(\d+)'[^>]*>\s*([^<]*)", html)[:8])
open(EV + r"\setup-pages.html", "w").write(html)
pickle.dump(p.pid, open(EV + r"\run2.pid", "wb"))
