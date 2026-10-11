"""Extra: non-http (websocket) scopes bypass both middlewares by design (auth_middleware.py:121, helpers.py:274)."""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import common as C
mode, scratch = sys.argv[1], Path(sys.argv[2])
C.setup(mode, scratch)
ids = C.seed()
from autotester.ui.app import app
out = []
for path in ("/ws", "/live", "/websockify", "/auth/login", "/projects/alpha/env", "/", "/docs"):
    sent = []
    async def receive():
        if not sent:
            sent.append("c")
            return {"type": "websocket.connect"}
        await asyncio.sleep(0.2)
        return {"type": "websocket.disconnect", "code": 1000}
    async def send(m):
        sent.append(m["type"] + ":" + str(m.get("code", "")))
    scope = {"type": "websocket", "asgi": {"version": "3.0"}, "scheme": "ws", "path": path, "raw_path": path.encode(),
             "query_string": b"", "root_path": "", "headers": [(b"host", b"evil.example"), (b"origin", b"http://evil.example")],
             "client": ("198.51.100.9", 1), "server": ("testserver", 80), "subprotocols": [], "state": {}}
    try:
        C.LOOP.run_until_complete(asyncio.wait_for(app(scope, receive, send), 5))
        out.append((path, sent[1:]))
    except BaseException as e:
        out.append((path, repr(e)[:80]))
print(mode, "websocket scopes (Host+Origin evil, no cookie):", out)
from autotester.ui.app import app as a
ws_routes = [r.path for r in a.router.routes if type(r).__name__ in ("WebSocketRoute", "APIWebSocketRoute")]
print("registered websocket routes:", ws_routes)
