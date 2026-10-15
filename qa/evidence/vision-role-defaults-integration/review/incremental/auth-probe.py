import asyncio,json
from starlette.requests import Request
from autotester.auth.policy import ROUTE_POLICY,SESSION
from autotester.schema.auth import Principal
from autotester.ui.auth_middleware import _refusal
import autotester
async def run():
 pending=Principal(user_id=2,email="pending@test.invalid")
 placed=Principal(user_id=3,email="placed@test.invalid",permissions=frozenset({"project.view"}))
 def request(method):return Request({"type":"http","method":method,"path":"/profile","headers":[],"scheme":"http","server":("test",80),"query_string":b""})
 async def allowed(method,who):return await _refusal(request(method),ROUTE_POLICY[(method,"/profile")],{},who)
 assert await allowed("GET",pending) is None
 assert (await allowed("POST",pending)).status_code==403,"pending profile write accepted"
 assert await allowed("POST",placed) is None
 assert (await allowed("POST",None)).status_code==401
 original=ROUTE_POLICY[("POST","/profile")]
 ROUTE_POLICY[("POST","/profile")]=SESSION
 killed=False
 try:
  assert (await allowed("POST",pending)) is not None,"pending profile write accepted"
 except AssertionError as exc:
  assert str(exc)=="pending profile write accepted";killed=True
 finally:ROUTE_POLICY[("POST","/profile")]=original
 assert killed
 assert (await allowed("POST",pending)).status_code==403
 print(json.dumps({"status":"passed","import":autotester.__file__,"cases":["pending GET allowed","pending POST403","placed POST allowed","anonymous POST401"],"mutation":"runtime actual POST rule MEMBER->SESSION","named_failure":"pending profile write accepted","restored_green":True,"source_edits":False}))
asyncio.run(run())
