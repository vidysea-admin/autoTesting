import socket, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import autotester; print(autotester.__file__)
from autotester.browser import launch
def raw(payload):
    srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)
    def run():
        c,_ = srv.accept(); c.recv(4096); c.sendall(payload); c.close()
    threading.Thread(target=run, daemon=True).start(); return srv.getsockname()[1]
def js(body):
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(body)
        def log_message(self,*a): pass
    s = HTTPServer(("127.0.0.1",0),H); threading.Thread(target=s.serve_forever,daemon=True).start(); return s.server_address[1]
for name, port in [("non-HTTP garbage", raw(b"garbage line\r\n\r\n")), ("json list []", js(b"[]")), ("json string", js(b'"x"')), ("json null", js(b"null")), ("json dict ok-but-no-key", js(b"{}"))]:
    try: print(name, "->", launch._answers_as(port, "/devtools/browser/abc"))
    except BaseException as e: print(name, "-> ESCAPES", type(e).__name__, e)
