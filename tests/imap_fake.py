"""A fake IMAP server for T-212: real sockets, a scripted mailbox, and a record of every command.

`FakeImap` listens on 127.0.0.1 and speaks just enough IMAP4 for `imaplib` to log in, EXAMINE a
folder, UID SEARCH and UID FETCH. It records each command line it receives (the LOGIN line is
recorded as the bare word, never its arguments) so a test can prove which verbs the reader sent
(MP16). It deliberately ANSWERS the write verbs (STORE, COPY, ...) instead of refusing them, so a
reader that sent one would be seen sending it. A plain `FETCH ... BODY[]` (no PEEK) marks the
message `\\Seen` in `FakeImap.seen`, the side effect BODY.PEEK exists to avoid. No product code, no
network beyond loopback, and every message is synthetic (MPI2).
"""

from __future__ import annotations

import re
import socketserver
import threading
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime

USER = "qa-mailbox-user"
PASSWORD = "Mb0x-pass-w0rd-canary"


@dataclass
class StoredMail:
    uid: int
    raw: bytes
    to: str


def make_mail(uid: int, *, subject: str, body: str, to: str = "role.b@example.test",
              sent: datetime | None = None) -> StoredMail:
    msg = EmailMessage()
    msg["From"] = "noreply@portal.example.test"
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = format_datetime(sent) if sent else "Mon, 19 Oct 2026 09:00:00 +0000"
    msg.set_content(body)
    return StoredMail(uid=uid, raw=bytes(msg), to=to)


@dataclass
class FakeImap:
    mails: list[StoredMail] = field(default_factory=list)
    honour_to_filter: bool = True
    commands: list[str] = field(default_factory=list)
    seen: set[int] = field(default_factory=set)
    _server: socketserver.ThreadingTCPServer | None = None

    def __enter__(self) -> FakeImap:
        outer = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:
                outer._serve(self)

        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self._server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc: object) -> None:
        assert self._server is not None
        self._server.shutdown()
        self._server.server_close()

    @property
    def address(self) -> str:
        assert self._server is not None
        return f"127.0.0.1:{self._server.server_address[1]}"

    def verbs(self) -> list[str]:
        """The first word of each recorded command (`UID` stays `UID`)."""
        return [c.split(" ", 1)[0].upper() for c in self.commands]

    def _serve(self, h: socketserver.StreamRequestHandler) -> None:
        h.wfile.write(b"* OK fake IMAP ready\r\n")
        for raw in h.rfile:
            tag, _, rest = raw.decode("utf-8", "replace").rstrip("\r\n").partition(" ")
            verb, _, args = rest.partition(" ")
            self.commands.append("LOGIN" if verb.upper() == "LOGIN" else rest)
            out = self._answer(tag, verb.upper(), args)
            h.wfile.write(out)
            if verb.upper() == "LOGOUT":
                return

    def _answer(self, tag: str, verb: str, args: str) -> bytes:
        t = tag.encode()
        if verb == "CAPABILITY":
            return b"* CAPABILITY IMAP4rev1\r\n" + t + b" OK done\r\n"
        if verb == "LOGIN":
            ok = USER in args and PASSWORD in args
            return t + (b" OK logged in\r\n" if ok else b" NO [AUTHENTICATIONFAILED] refused\r\n")
        if verb in ("EXAMINE", "SELECT"):
            if "NoSuchFolder" in args:
                return t + b" NO no such folder\r\n"
            mode = b"READ-ONLY" if verb == "EXAMINE" else b"READ-WRITE"
            return f"* {len(self.mails)} EXISTS\r\n".encode() + t + b" OK [" + mode + b"] done\r\n"
        if verb == "UID":
            return self._uid(t, args)
        if verb == "LOGOUT":
            return b"* BYE bye\r\n" + t + b" OK logout\r\n"
        return t + b" OK noted\r\n"          # NOOP and every write verb: answered, so it is seen

    def _uid(self, t: bytes, args: str) -> bytes:
        sub, _, rest = args.partition(" ")
        if sub.upper() == "SEARCH":
            want = re.search(r'TO\s+"?([^"\s]+)"?', rest)
            hits = [m.uid for m in self.mails
                    if not (self.honour_to_filter and want) or want.group(1) in m.to]
            return b"* SEARCH " + " ".join(map(str, hits)).encode() + b"\r\n" + t + b" OK done\r\n"
        if sub.upper() == "FETCH":
            uid = int(rest.split(" ", 1)[0])
            mail = next(m for m in self.mails if m.uid == uid)
            if "PEEK" not in rest.upper():
                self.seen.add(uid)
            head = f"* {uid} FETCH (UID {uid} BODY[]<0> {{{len(mail.raw)}}}\r\n".encode()
            return head + mail.raw + b")\r\n" + t + b" OK done\r\n"
        return t + b" OK noted\r\n"
